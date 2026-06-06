"""
Cut and compress video segments with ffmpeg so they can be sent to the
Seed video-understanding API (base64 data URI). Segments are downscaled and
audio is kept (mono 16 kHz) so the model can do ASR on the spoken content.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def extract_clip(
    video_path: str | Path,
    start_sec: float,
    end_sec: float,
    max_height: int = 480,
) -> Path | None:
    """
    Cut [start_sec, end_sec] from video_path into a compressed temp mp4.
    Returns the clip path, or None on failure. Caller is responsible for
    deleting the returned file.
    """
    video_path = Path(video_path)
    duration = max(0.1, end_sec - start_sec)

    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    out_path = Path(tmp.name)
    tmp.close()

    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", f"{start_sec}",
                "-i", str(video_path),
                "-t", f"{duration}",
                "-vf", f"scale=-2:{max_height}",
                "-r", "2",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "30",
                "-c:a", "aac",
                "-ac", "1",
                "-ar", "16000",
                "-b:a", "32k",
                "-movflags", "+faststart",
                str(out_path),
            ],
            capture_output=True,
            timeout=600,
            check=True,
        )
        if out_path.exists() and out_path.stat().st_size > 0:
            return out_path
    except Exception:
        pass

    # Cleanup on failure
    out_path.unlink(missing_ok=True)
    return None


def generate_ad_clip(
    video_path: str | Path,
    start_sec: float,
    end_sec: float,
    output_path: Path,
) -> bool:
    """
    Cut [start_sec, end_sec] from video_path into a high-quality mp4 for export.
    Preserves resolution and quality.
    """
    duration = max(0.1, end_sec - start_sec)
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", f"{start_sec}",
                "-i", str(video_path),
                "-t", f"{duration}",
                "-c:v", "libx264",
                "-preset", "slow",
                "-crf", "22",
                "-c:a", "aac",
                "-b:a", "192k",
                str(output_path),
            ],
            capture_output=True,
            timeout=600,
            check=True,
        )
        return output_path.exists() and output_path.stat().st_size > 0
    except Exception:
        return False
