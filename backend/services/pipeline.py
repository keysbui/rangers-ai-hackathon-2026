"""
Full video processing pipeline orchestrator.
Called as a background task after video upload.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from db import get_db
from services.scene_service import detect_scenes
from services.frame_service import extract_frames, get_frames_in_range
from services.seed_client import analyze_segment, analyze_segment_video
from services.clip_service import extract_clip
from config import THUMBNAIL_DIR


def _get_duration(video_path: str) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", video_path],
            capture_output=True, text=True, timeout=60,
        )
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])
    except Exception:
        return 0.0


def run_pipeline(video_id: str, video_path: str):
    """Main pipeline: scene detect -> frame extract -> Seed analysis -> store."""
    try:
        with get_db() as conn:
            conn.execute(
                "UPDATE Videos SET status='processing' WHERE id=?", (video_id,)
            )

        # Get duration
        duration = _get_duration(video_path)
        if duration > 0:
            with get_db() as conn:
                conn.execute(
                    "UPDATE Videos SET duration=? WHERE id=?", (duration, video_id)
                )

        # Step 1: Extract all frames at 1fps
        frame_paths = extract_frames(video_path, video_id)

        # Step 2: Detect scene boundaries
        scenes = detect_scenes(video_path)

        # Step 3: For each scene, analyze with Seed.
        # Prefer sending the actual video clip (audio + visuals) so the model
        # can transcribe speech (ASR); fall back to frames if clipping fails.
        for start_sec, end_sec in scenes:
            clip_path = extract_clip(video_path, start_sec, end_sec)
            analysis = None
            if clip_path is not None:
                try:
                    analysis = analyze_segment_video(clip_path, start_sec, end_sec)
                except Exception:
                    analysis = None
                finally:
                    clip_path.unlink(missing_ok=True)

            if analysis is None:
                frames_in_scene = get_frames_in_range(video_id, start_sec, end_sec)
                analysis = analyze_segment(
                    frame_paths=frames_in_scene,
                    start_sec=start_sec,
                    end_sec=end_sec,
                )

            # Pick thumbnail as the middle frame of the scene
            mid_sec = (start_sec + end_sec) / 2
            mid_idx = max(1, round(mid_sec) + 1)
            thumb_path = THUMBNAIL_DIR / video_id / f"{mid_idx:06d}.jpg"
            thumb_url = (
                f"/thumbnails/{video_id}/{mid_idx:06d}.jpg"
                if thumb_path.exists()
                else None
            )

            with get_db() as conn:
                conn.execute(
                    """
                    INSERT INTO Timeline_Metadata
                        (video_id, timestamp_start, timestamp_end,
                         transcript, ocr_text, audio_event,
                         detected_skus, energy_score, thumbnail_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        video_id,
                        start_sec,
                        end_sec,
                        analysis.get("transcript", ""),
                        analysis.get("ocr_text", ""),
                        analysis.get("audio_event", ""),
                        analysis.get("detected_skus", ""),
                        float(analysis.get("energy_score", 0.0)),
                        thumb_url,
                    ),
                )

        with get_db() as conn:
            conn.execute(
                "UPDATE Videos SET status='done' WHERE id=?", (video_id,)
            )

    except Exception as exc:
        with get_db() as conn:
            conn.execute(
                "UPDATE Videos SET status='error' WHERE id=?", (video_id,)
            )
        raise
