import json
from typing import Annotated, List, LiteralString

import fsspec
from fastapi import FastAPI, Form, Header, HTTPException, UploadFile
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

    items: List[Object] = []

    completed_path = f"{BUCKET_NAME}/{COMPLETED_PATH}"
    uploads_path = f"{BUCKET_NAME}/{UPLOADS_PATH}"

    if fs.isdir(completed_path):
        for file in fs.ls(completed_path):
            items.append(Object(path=str(file).replace(completed_path, ""), n_bytes=fs.size(file)))

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

    fs.invalidate_cache()

    return ObjectList(items=items)


@app.post("/objects")
async def upload_file(
    file: UploadFile,
    chunk_index: Annotated[int, Form(alias="chunkIndex")],
    total_chunks: Annotated[int, Form(alias="totalChunks")],
    content_range: Annotated[str | None, Header()] = None,
) -> Response:
    """Upload a file."""

    fs = fsspec.filesystem(protocol="s3")

    print(f"Received: {file.filename}, {chunk_index}, {total_chunks}, {content_range}")

    if not content_range:
        raise HTTPException(status_code=400, detail="Content-Range header is missing")

    bytes_range, file_size = content_range.split(" ")[1].split("/")
    start, end = map(int, bytes_range.split("-"))
    filename = f"{BUCKET_NAME}/{UPLOADS_PATH}/{file.filename}"
    parts_path = f"{filename}.part"

    def part_filename_fn(ichunk):
        return f"{parts_path}/.part{ichunk:05x}"

    if not fs.exists(metadata_path := f"{parts_path}/metadata.json"):
        with fs.open(metadata_path, "w") as f:
            json.dump({"total_chunks": total_chunks, "total_size": file_size}, f)

    with fs.open(part_filename_fn(chunk_index), "wb") as f:
        f.write(await file.read())

    if chunk_index == total_chunks - 1:
        with fs.open(filename, "wb") as combined_file:
            for ichunk in range(total_chunks):
                with fs.open(part_filename_fn(ichunk), "rb") as part_file:
                    combined_file.write(part_file.read())

        fs.rm(parts_path, recursive=True)

        fs.mv(filename, f"{BUCKET_NAME}/{COMPLETED_PATH}/{file.filename}")

        return Response(status_code=200, content="File uploaded successfully")

    return Response(
        content=f"Chunk {chunk_index} received",
        status_code=206,
        headers={"Range": f"bytes={start}-{end}"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
