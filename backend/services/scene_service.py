"""
Detect scene boundaries using PySceneDetect.
Returns a list of (start_sec, end_sec) tuples for each detected shot.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Tuple

from config import SCENE_FALLBACK_ENABLED, SCENE_FALLBACK_CHUNK_SEC


def detect_scenes(video_path: str | Path) -> List[Tuple[float, float]]:
    """
    Use PySceneDetect CLI to detect scene cuts and return shot intervals.

    If SCENE_FALLBACK_ENABLED is True (default), falls back to fixed-size
    chunking when PySceneDetect fails or returns 0 scenes.
    If False, raises RuntimeError so the caller is forced to fix the detector.
    """
    video_path = Path(video_path)
    exc_info: Exception | None = None

    try:
        subprocess.run(
            [
                "scenedetect",
                "--input", str(video_path),
                "detect-content",
                "list-scenes",
                "--output", str(video_path.parent),
                "--filename", f"{video_path.stem}-scenes",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        csv_file = video_path.parent / f"{video_path.stem}-scenes.csv"
        if csv_file.exists():
            scenes = _parse_scene_csv(csv_file)
            if scenes:
                return scenes
    except Exception as exc:
        exc_info = exc

    if not SCENE_FALLBACK_ENABLED:
        if exc_info is not None:
            raise RuntimeError(
                f"PySceneDetect failed for {video_path}: {exc_info}"
            ) from exc_info
        raise RuntimeError(
            f"PySceneDetect returned 0 scenes for {video_path} "
            "and SCENE_FALLBACK_ENABLED is false."
        )

    return _fallback_chunks(video_path, chunk_sec=SCENE_FALLBACK_CHUNK_SEC)


def _parse_scene_csv(csv_path: Path) -> List[Tuple[float, float]]:
    """
    PySceneDetect CSV columns (0-indexed):
      0: Scene Number
      1: Start Frame
      2: Start Timecode   (HH:MM:SS.mmm)
      3: Start Time (seconds)
      4: End Frame
      5: End Timecode     (HH:MM:SS.mmm)
      6: End Time (seconds)
      ...
    Skip header rows (start with "Scene" or "Timecode").
    Use the pre-computed seconds columns (3 & 6) directly.
    """
    scenes: List[Tuple[float, float]] = []
    with open(csv_path) as f:
        lines = f.readlines()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("Scene") or stripped.startswith("Timecode"):
            continue
        parts = stripped.split(",")
        if len(parts) >= 7:
            try:
                start_sec = float(parts[3].strip())
                end_sec = float(parts[6].strip())
                scenes.append((start_sec, end_sec))
            except Exception:
                continue
    return scenes



def _fallback_chunks(video_path: Path, chunk_sec: int = 30) -> List[Tuple[float, float]]:
    """Get video duration via ffprobe then split into equal chunks."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", str(video_path),
            ],
            capture_output=True, text=True, timeout=60,
        )
        import json
        info = json.loads(result.stdout)
        duration = float(info["format"]["duration"])
    except Exception:
        duration = 3600.0

    chunks = []
    t = 0.0
    while t < duration:
        end = min(t + chunk_sec, duration)
        chunks.append((t, end))
        t = end
    return chunks
