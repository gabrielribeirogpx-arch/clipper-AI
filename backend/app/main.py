from pathlib import Path
from typing import Iterator

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.api.upload import router as upload_router
from app.api.timeline import router as timeline_router

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
CLIPS_DIR = BASE_DIR / "clips"
CHUNK_SIZE = 1024 * 1024


# =========================================
# CORS
# =========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# =========================================
# ROUTES
# =========================================

app.include_router(upload_router)
app.include_router(timeline_router)


# =========================================
# MEDIA STREAMING
# =========================================

def _iter_file(path: Path, start: int, end: int) -> Iterator[bytes]:
    with path.open("rb") as file:
        file.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = file.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


@app.get("/media/{file_path:path}")
async def stream_media(request: Request, file_path: str, range: str | None = Header(default=None)):
    media_path = (CLIPS_DIR / file_path).resolve()
    try:
        media_path.relative_to(CLIPS_DIR.resolve())
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid media path") from error

    print(f"[MEDIA REQUEST] method={request.method} path={request.url.path} range={range}")

    if not media_path.exists() or not media_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    file_size = media_path.stat().st_size
    headers = {
        "Accept-Ranges": "bytes",
        "Access-Control-Expose-Headers": "*",
    }

    if range:
        print(f"[VIDEO STREAM] partial range={range} file={media_path}")
        try:
            units, range_spec = range.split("=", 1)
            if units.strip() != "bytes":
                raise ValueError("Invalid range unit")
            start_str, end_str = range_spec.split("-", 1)
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1
        except Exception as error:
            raise HTTPException(status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE, detail="Invalid range header") from error

        start = max(0, start)
        end = min(end, file_size - 1)
        if start > end or start >= file_size:
            raise HTTPException(status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE, detail="Requested range not satisfiable")

        content_length = end - start + 1
        headers.update(
            {
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(content_length),
                "Content-Type": "video/mp4",
            }
        )
        print(f"[MEDIA RESPONSE] status=206 content_length={content_length} path={media_path}")
        return StreamingResponse(
            _iter_file(media_path, start, end),
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            headers=headers,
            media_type="video/mp4",
        )

    headers.update({"Content-Length": str(file_size)})
    media_type = "video/mp4" if media_path.suffix.lower() == ".mp4" else "application/octet-stream"
    print(f"[MEDIA RESPONSE] status=200 content_length={file_size} path={media_path}")
    return StreamingResponse(_iter_file(media_path, 0, file_size - 1), headers=headers, media_type=media_type)


# =========================================
# HEALTH CHECK
# =========================================


@app.get("/")
def root():
    return {"status": "running"}
