"""
Single-Stage Long-Context Retrieval Engine:
  Fetch every segment of the video ordered by timestamp and send the full
  timeline to Seed-2.0-mini in one call so the model can reason over the
  entire context without being constrained by keyword matching.

  Rationale: Vietnamese word-segmentation and synonym variation caused FTS5
  keyword search to miss relevant segments.  The trade-off is higher token
  usage per query, which is acceptable as long as the video timeline fits
  within the model's context window.
"""
from __future__ import annotations

import time
from typing import Any

from db import get_db
from services.seed_client import answer_question
from config import THUMBNAIL_DIR


def _thumbnail_url(video_id: str, timestamp: float) -> str | None:
    frame_idx = max(1, round(timestamp) + 1)
    full = THUMBNAIL_DIR / video_id / f"{frame_idx:06d}.jpg"
    return f"/thumbnails/{video_id}/{frame_idx:06d}.jpg" if full.exists() else None


def _segment_end_for(segments: list[dict], ts: float) -> float | None:
    """
    Return the timestamp_end of the segment whose time range contains *ts*.
    Falls back to the end of the last segment when *ts* is beyond all ranges,
    and to None when *segments* is empty.
    """
    if not segments:
        return None
    for seg in segments:
        if seg["timestamp_start"] <= ts <= seg["timestamp_end"]:
            return seg["timestamp_end"]
    # ts is past the last segment — return the last segment's end
    return segments[-1]["timestamp_end"]


def retrieve_and_answer(
    video_id: str,
    question: str,
    language: str = "vi",
) -> dict[str, Any]:
    """
    Single-stage retrieval: load the full segment timeline for *video_id* and
    send it to the LLM so it can reason over every moment without keyword bias.
    """
    t0 = time.time()

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT timestamp_start, timestamp_end, transcript,
                   ocr_text, audio_event, detected_skus
            FROM Timeline_Metadata
            WHERE video_id = ?
            ORDER BY timestamp_start
            """,
            (video_id,),
        ).fetchall()

    if not rows:
        total_ms = (time.time() - t0) * 1000
        return {
            "answer": "No video data found. Please process the video first.",
            "timestamp": None,
            "timestamp_end": None,
            "thumbnail_url": None,
            "reasoning_proof": "No segments available.",
            "tokens_used": {"input": 0, "output": 0, "cache_read": 0},
            "latency_ms": total_ms,
        }

    segment_data = [
        {
            "timestamp_start": row["timestamp_start"],
            "timestamp_end": row["timestamp_end"],
            "transcript": row["transcript"],
            "ocr_text": row["ocr_text"],
            "audio_event": row["audio_event"],
            "detected_skus": row["detected_skus"],
        }
        for row in rows
    ]

    seed_result = answer_question(
        segment_data=segment_data,
        question=question,
        language=language,
    )

    answer_ts = seed_result.get("timestamp") or rows[0]["timestamp_start"]
    answer_ts_end = _segment_end_for(segment_data, float(answer_ts))
    thumb = _thumbnail_url(video_id, float(answer_ts))

    total_ms = (time.time() - t0) * 1000
    return {
        "answer": seed_result.get("answer", ""),
        "timestamp": answer_ts,
        "timestamp_end": answer_ts_end,
        "thumbnail_url": thumb,
        "reasoning_proof": seed_result.get("reasoning_proof", ""),
        "tokens_used": seed_result.get("_tokens", {"input": 0, "output": 0, "cache_read": 0}),
        "latency_ms": total_ms,
    }
