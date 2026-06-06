"""
Video management endpoints:
  POST /api/videos        - upload local file or provide URL
  GET  /api/videos        - list all videos
  GET  /api/videos/{id}   - get single video
  POST /api/videos/{id}/process - trigger processing pipeline
"""
from __future__ import annotations

import asyncio
import uuid
import shutil
from pathlib import Path

import aiofiles
import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, BackgroundTasks, Request
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse

from config import RAW_VIDEO_DIR, THUMBNAIL_DIR
from db import get_db
from models.video import VideoResponse, VideoStatus
from services import pipeline

router = APIRouter(prefix="/api/videos", tags=["videos"])

_MIME = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
}


def _find_video_file(video_id: str) -> Path | None:
    candidates = list(RAW_VIDEO_DIR.glob(f"{video_id}.*"))
    return candidates[0] if candidates else None


def _row_to_video(row) -> VideoResponse:
    return VideoResponse(
        id=row["id"],
        name=row["name"],
        url=row["url"],
        duration=row["duration"],
        status=VideoStatus(row["status"]),
        created_at=row["created_at"],
    )


@router.post("", response_model=VideoResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile | None = File(default=None),
    url: str | None = Form(default=None),
    auto_process: bool = Form(default=True),
):
    if not file and not url:
        raise HTTPException(status_code=422, detail="Provide either a file upload or a URL.")

    video_id = str(uuid.uuid4())

    if file:
        ext = Path(file.filename or "video.mp4").suffix or ".mp4"
        name = file.filename or f"video{ext}"
        dest = RAW_VIDEO_DIR / f"{video_id}{ext}"
        async with aiofiles.open(dest, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                await f.write(chunk)
        video_url = None
        local_path = str(dest)
    else:
        name = url.split("/")[-1].split("?")[0] or "video.mp4"
        ext = Path(name).suffix or ".mp4"
        dest = RAW_VIDEO_DIR / f"{video_id}{ext}"
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                async with aiofiles.open(dest, "wb") as f:
                    async for chunk in resp.aiter_bytes(1024 * 1024):
                        await f.write(chunk)
        video_url = url
        local_path = str(dest)

    with get_db() as conn:
        conn.execute(
            "INSERT INTO Videos (id, name, url, status) VALUES (?, ?, ?, ?)",
            (video_id, name, video_url, "pending"),
        )

    if auto_process:
        background_tasks.add_task(pipeline.run_pipeline, video_id, local_path)

    with get_db() as conn:
        row = conn.execute("SELECT * FROM Videos WHERE id=?", (video_id,)).fetchone()

    return _row_to_video(row)


@router.get("", response_model=list[VideoResponse])
def list_videos():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM Videos ORDER BY created_at DESC").fetchall()
    return [_row_to_video(r) for r in rows]


@router.get("/{video_id}", response_model=VideoResponse)
def get_video(video_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM Videos WHERE id=?", (video_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Video not found")
    return _row_to_video(row)


@router.get("/{video_id}/stream")
def stream_video(video_id: str, request: Request):
    """Stream the raw video file with HTTP Range support (for seeking)."""
    path = _find_video_file(video_id)
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="Video file not found on disk")

    file_size = path.stat().st_size
    media_type = _MIME.get(path.suffix.lower(), "application/octet-stream")
    range_header = request.headers.get("range")

    if range_header is None:
        return FileResponse(str(path), media_type=media_type)

    # Parse "bytes=start-end"
    try:
        units, _, rng = range_header.partition("=")
        start_s, _, end_s = rng.partition("-")
        start = int(start_s) if start_s else 0
        end = int(end_s) if end_s else file_size - 1
    except ValueError:
        raise HTTPException(status_code=416, detail="Invalid Range header")

    start = max(0, start)
    end = min(end, file_size - 1)
    chunk_size = end - start + 1

    def iter_file():
        with open(path, "rb") as f:
            f.seek(start)
            remaining = chunk_size
            while remaining > 0:
                data = f.read(min(1024 * 1024, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_size),
    }
    return StreamingResponse(
        iter_file(), status_code=206, media_type=media_type, headers=headers
    )


@router.get("/{video_id}/timeline")
def get_timeline(video_id: str):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM Timeline_Metadata WHERE video_id=? ORDER BY timestamp_start",
            (video_id,),
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/{video_id}/process")
async def reprocess_video(video_id: str, background_tasks: BackgroundTasks):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM Videos WHERE id=?", (video_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Video not found")

    # Find local file
    candidates = list(RAW_VIDEO_DIR.glob(f"{video_id}.*"))
    if not candidates:
        raise HTTPException(status_code=404, detail="Video file not found on disk")

    background_tasks.add_task(pipeline.run_pipeline, video_id, str(candidates[0]))
    return {"status": "processing_started", "video_id": video_id}


@router.delete("/{video_id}")
def delete_video(video_id: str):
    """Delete a video from DB and disk (video file + thumbnails)."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM Videos WHERE id=?", (video_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Video not found")

        # 1. Delete from DB
        conn.execute("DELETE FROM Videos WHERE id=?", (video_id,))
        conn.execute("DELETE FROM Timeline_Metadata WHERE video_id=?", (video_id,))

    # 2. Delete physical video file
    video_path = _find_video_file(video_id)
    if video_path and video_path.exists():
        video_path.unlink()

    # 3. Delete thumbnails/frames directory
    thumb_dir = THUMBNAIL_DIR / video_id
    if thumb_dir.exists() and thumb_dir.is_dir():
        shutil.rmtree(thumb_dir)

    # 4. Delete scene detection CSV if exists
    scene_csv = RAW_VIDEO_DIR / f"{video_id}-scenes.csv"
    if scene_csv.exists():
        scene_csv.unlink()

    return {"status": "deleted", "video_id": video_id}
