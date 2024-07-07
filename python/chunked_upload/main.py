import hashlib
import json
from typing import Annotated, List, LiteralString

import fsspec
from fastapi import BackgroundTasks, FastAPI, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response

from .models import Object, ObjectList

BUCKET_NAME: LiteralString = "storage"
COMPLETED_PATH: LiteralString = "completed"
UPLOADS_PATH: LiteralString = "uploads"

app = FastAPI()


@app.get("/objects")
async def list_objects() -> ObjectList:
    """Return a list of objects in storage."""

    fs = fsspec.filesystem(protocol="s3")
    fs.invalidate_cache()

    items: List[Object] = []

    completed_path = f"{BUCKET_NAME}/{COMPLETED_PATH}"
    uploads_path = f"{BUCKET_NAME}/{UPLOADS_PATH}"

    if fs.isdir(completed_path):
        for file in fs.ls(completed_path):
            items.append(
                Object(
                    path=str(file).replace(completed_path, ""),
                    n_bytes=fs.size(file),
                )
            )

    if fs.isdir(uploads_path):
        for file in fs.ls(uploads_path):
            try:
                with fs.open(f"{file}/metadata.json") as f:
                    metadata = json.load(f)

                items.append(
                    Object(
                        path=str(file).replace(uploads_path, ""),
                        uploaded_chunks=len(fs.glob(f"{file}/.part*")),
                        total_chunks=metadata["total_chunks"],
                        n_bytes=metadata["total_size"],
                        completed=False,
                        finalizing=metadata["finalizing"],
                    )
                )

            except Exception:
                items.append(
                    Object(
                        path=str(file).replace(uploads_path, ""),
                        uploaded_chunks=1,
                        total_chunks=1,
                        n_bytes=0,
                        completed=False,
                    )
                )

    print(f"Found {len(items)} objects.")

    return ObjectList(items=items)


@app.delete("/objects/{filename}")
async def delete_object(filename: str) -> None:
    """Delete an object."""

    fs = fsspec.filesystem(protocol="s3")
    fs.invalidate_cache()

    fs.rm(f"{BUCKET_NAME}/{COMPLETED_PATH}/{filename}")

    print(f"Deleted {filename}")


def part_filename(parts_path: str, ichunk: int):
    """Return the filename of a part."""

    return f"{parts_path}/.part{ichunk:05x}"


def complete_upload(filename: str, parts_path: str, total_chunks: int) -> None:
    """Complete an upload."""

    print(f"Finalizing upload of `{filename}`")

    fs = fsspec.filesystem(protocol="s3")
    fs.invalidate_cache()

    with fs.open(metadata_path := f"{parts_path}/metadata.json", "r") as f:
        metadata = json.load(f)

    metadata["finalizing"] = True

    with fs.open(metadata_path, "w") as f:
        json.dump(metadata, f)

    dest_path = f"{BUCKET_NAME}/{COMPLETED_PATH}/{filename}"

    with fs.open(dest_path, "wb") as combined_file:
        for ichunk in range(total_chunks):
            with fs.open(part_path := part_filename(parts_path, ichunk), "rb") as part_file:
                combined_file.write(part_file.read())

            fs.rm(part_path)

    fs.rm(parts_path, recursive=True)

    print(
        f"Completed upload to `{dest_path}`: "
        f"`{hashlib.sha256(fs.open(dest_path, "rb").read()).digest().hex()}`"
    )


@app.post("/objects")
async def upload_file(
    file: UploadFile,
    chunk_index: Annotated[int, Form(alias="chunkIndex")],
    total_chunks: Annotated[int, Form(alias="totalChunks")],
    background_tasks: BackgroundTasks,
    content_range: Annotated[str | None, Header()] = None,
) -> Response:
    """Upload a file."""

    fs = fsspec.filesystem(protocol="s3")
    fs.invalidate_cache()

    print(f"Received: {file.filename}, {chunk_index}, {total_chunks}, {content_range}")

    if not content_range:
        raise HTTPException(status_code=400, detail="Content-Range header is missing")

    bytes_range, file_size = content_range.split(" ")[1].split("/")
    start, end = map(int, bytes_range.split("-"))
    filename = f"{BUCKET_NAME}/{UPLOADS_PATH}/{file.filename}"
    parts_path = f"{filename}.part"

    if not fs.exists(metadata_path := f"{parts_path}/metadata.json"):
        with fs.open(metadata_path, "w") as f:
            json.dump(
                {"total_chunks": total_chunks, "total_size": file_size, "finalizing": False}, f
            )

    with fs.open(part_filename(parts_path, chunk_index), "wb") as f:
        f.write(await file.read())

    if chunk_index == total_chunks - 1:
        background_tasks.add_task(complete_upload, file.filename, parts_path, total_chunks)
        return Response(status_code=200, content="File uploaded successfully")

    return Response(
        content=f"Chunk {chunk_index} received",
        status_code=206,
        headers={"Range": f"bytes={start}-{end}"},
    )
