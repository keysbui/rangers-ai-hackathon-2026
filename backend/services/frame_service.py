"""
Extract frames from video using ffmpeg at 1 frame/second.
Frames saved to storage/thumbnails/{video_id}/{timestamp}.jpg
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List

from config import THUMBNAIL_DIR


def extract_frames(video_path: str | Path, video_id: str) -> List[Path]:
    """
    Extract 1 frame per second from video_path.
    Returns sorted list of saved frame paths.
    """
    video_path = Path(video_path)
    out_dir = THUMBNAIL_DIR / video_id
    out_dir.mkdir(parents=True, exist_ok=True)

    pattern = str(out_dir / "%06d.jpg")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", "fps=1",
            "-q:v", "3",
            pattern,
        ],
        capture_output=True,
        timeout=3600,
        check=True,
    )

    frames = sorted(out_dir.glob("*.jpg"))
    return frames


def get_frame_path(video_id: str, timestamp_sec: float) -> Path | None:
    """Return closest frame path for a given timestamp (1fps naming)."""
    out_dir = THUMBNAIL_DIR / video_id
    frame_idx = max(1, round(timestamp_sec) + 1)
    path = out_dir / f"{frame_idx:06d}.jpg"
    if path.exists():
        return path
    frames = sorted(out_dir.glob("*.jpg"))
    return frames[0] if frames else None


def get_frames_in_range(video_id: str, start_sec: float, end_sec: float) -> List[Path]:
    """Return all frame paths within a timestamp range."""
    out_dir = THUMBNAIL_DIR / video_id
    start_idx = max(1, int(start_sec) + 1)
    end_idx = int(end_sec) + 1
    frames = []
    for idx in range(start_idx, end_idx + 1):
        p = out_dir / f"{idx:06d}.jpg"
        if p.exists():
            frames.append(p)
    return frames
