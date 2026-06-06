#!/usr/bin/env python3
"""
Debug script for PySceneDetect.

Usage:
    python scripts/test_scene_detect.py <video_path> [--chunk-sec 30]

Options:
    --chunk-sec   Size of fallback chunks in seconds (default: 30).
                  Only used when SCENE_FALLBACK_ENABLED=true.

Environment:
    SCENE_FALLBACK_ENABLED   Set to "false" to error instead of falling back.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

# Allow running from repo root or from backend/
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import SCENE_FALLBACK_ENABLED, SCENE_FALLBACK_CHUNK_SEC  # noqa: E402



def _parse_scene_csv(csv_path: Path) -> list[tuple[float, float]]:
    """
    PySceneDetect CSV columns (0-indexed):
      0: Scene Number | 1: Start Frame | 2: Start Timecode
      3: Start Time (seconds) | 4: End Frame | 5: End Timecode
      6: End Time (seconds) | ...
    """
    scenes: list[tuple[float, float]] = []
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


def _get_duration(video_path: Path) -> float:
    import json
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(video_path)],
            capture_output=True, text=True, timeout=60,
        )
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])
    except Exception as exc:
        print(f"  [warn] ffprobe failed: {exc}")
        return 0.0


def _fallback_chunks(video_path: Path, chunk_sec: int) -> list[tuple[float, float]]:
    duration = _get_duration(video_path)
    if duration <= 0:
        duration = 3600.0
    chunks = []
    t = 0.0
    while t < duration:
        end = min(t + chunk_sec, duration)
        chunks.append((t, end))
        t = end
    return chunks


def main():
    parser = argparse.ArgumentParser(description="Debug PySceneDetect on a video file.")
    parser.add_argument("video", help="Path to the video file")
    parser.add_argument(
        "--chunk-sec",
        type=int,
        default=SCENE_FALLBACK_CHUNK_SEC,
        help=f"Fallback chunk size in seconds (default from config: {SCENE_FALLBACK_CHUNK_SEC})",
    )
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"[error] File not found: {video_path}")
        sys.exit(1)

    print(f"Video        : {video_path}")
    print(f"Fallback     : {'enabled' if SCENE_FALLBACK_ENABLED else 'DISABLED (will raise on failure)'}")
    print(f"Chunk size   : {args.chunk_sec}s")
    print(f"Duration     : {_get_duration(video_path):.2f}s")
    print()

    # --- Run PySceneDetect ---
    csv_file = video_path.parent / f"{video_path.stem}-scenes.csv"
    cmd = [
        "scenedetect",
        "--input", str(video_path),
        "detect-content",
        "list-scenes",
        "--output", str(video_path.parent),
        "--filename", f"{video_path.stem}-scenes",
    ]
    print(f"Running: {' '.join(cmd)}")
    print("-" * 60)

    t0 = time.time()
    exc_info: Exception | None = None
    try:
        result = subprocess.run(cmd, capture_output=False, text=True, timeout=300)
        elapsed = time.time() - t0
        print(f"\n[scenedetect exited {result.returncode} in {elapsed:.1f}s]")
    except Exception as exc:
        elapsed = time.time() - t0
        exc_info = exc
        print(f"\n[scenedetect raised {type(exc).__name__} after {elapsed:.1f}s: {exc}]")

    print("-" * 60)

    # --- Parse results ---
    scenes: list[tuple[float, float]] = []
    if exc_info is None and csv_file.exists():
        scenes = _parse_scene_csv(csv_file)
        print(f"CSV file     : {csv_file}")
        print(f"Scenes found : {len(scenes)}")
    else:
        if not csv_file.exists():
            print(f"CSV file     : NOT FOUND ({csv_file})")
        print(f"Scenes found : 0")

    if scenes:
        print()
        print(f"{'#':>4}  {'start':>10}  {'end':>10}  {'duration':>10}")
        print(f"{'—'*4}  {'—'*10}  {'—'*10}  {'—'*10}")
        for i, (s, e) in enumerate(scenes, 1):
            print(f"{i:>4}  {s:>10.3f}  {e:>10.3f}  {e - s:>10.3f}")
    else:
        # No scenes — decide fallback or error
        print()
        if not SCENE_FALLBACK_ENABLED:
            msg = (
                f"PySceneDetect failed: {exc_info}" if exc_info
                else "PySceneDetect returned 0 scenes"
            )
            print(f"[WOULD RAISE] RuntimeError: {msg}")
            print("             Set SCENE_FALLBACK_ENABLED=true to use chunked fallback instead.")
            sys.exit(2)
        else:
            chunks = _fallback_chunks(video_path, args.chunk_sec)
            print(f"[fallback] Using {len(chunks)} fixed chunks of {args.chunk_sec}s each:")
            print()
            print(f"{'#':>4}  {'start':>10}  {'end':>10}  {'duration':>10}")
            print(f"{'—'*4}  {'—'*10}  {'—'*10}  {'—'*10}")
            for i, (s, e) in enumerate(chunks, 1):
                print(f"{i:>4}  {s:>10.3f}  {e:>10.3f}  {e - s:>10.3f}")


if __name__ == "__main__":
    main()
