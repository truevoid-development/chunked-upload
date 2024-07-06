from typing import Optional

import fsspec
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response

app = FastAPI()

fs = fsspec.filesystem(protocol="s3")


@app.head("/")
async def upload_head():
    return Response(headers={"Accept-Ranges": "bytes"})


@app.post("/")
async def upload_file(
    file: UploadFile = File(...),  # noqa
    chunkIndex: int = Form(...),
    totalChunks: int = Form(...),
    content_range: Optional[str] = Header(None),
):
    print(f"Received: {file.filename}, {chunkIndex}, {totalChunks}, {content_range}")

    if not content_range:
        raise HTTPException(status_code=400, detail="Content-Range header is missing")

    bytes_range, file_size = content_range.split(" ")[1].split("/")
    start, end = map(int, bytes_range.split("-"))
    content = await file.read()
    filename = f"storage/{file.filename}"

    with fs.open(f"{filename}.part{chunkIndex}", "wb") as f:
        f.write(content)

    if chunkIndex == totalChunks - 1:
        with fs.open(filename, "wb") as combined_file:
            for ichunk in range(totalChunks):
                with fs.open(f"{filename}.part{ichunk}", "rb") as part_file:
                    combined_file.write(part_file.read())

                fs.rm(f"{filename}.part{ichunk}")

        return {"message": "File uploaded successfully"}

    return Response(
        content="Chunk received", status_code=206, headers={"Range": f"bytes={start}-{end}"}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
