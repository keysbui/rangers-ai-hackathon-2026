"""
Two-Stage Retrieval Engine:
  Stage 1: FTS5 keyword search on SQLite to find candidate segments.
  Stage 2: Send candidates + question to Seed-2.0-mini for deep reasoning.
"""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from db import get_db
from services.seed_client import answer_question
from services.frame_service import get_frame_path
from config import THUMBNAIL_DIR


def _thumbnail_url(video_id: str, timestamp: float) -> str | None:
    frame_idx = max(1, round(timestamp) + 1)
    full = THUMBNAIL_DIR / video_id / f"{frame_idx:06d}.jpg"
    return f"/thumbnails/{video_id}/{frame_idx:06d}.jpg" if full.exists() else None


def _build_fts_query(question: str) -> str:
    """
    Convert a free-text question into a safe FTS5 MATCH query.
    Extracts Unicode word tokens, quotes each one, and joins with OR
    so punctuation like '?' or ':' cannot break FTS5 syntax.
    """
    tokens = re.findall(r"\w+", question, flags=re.UNICODE)
    # Drop very short tokens (single chars) to reduce noise
    tokens = [t for t in tokens if len(t) > 1]
    if not tokens:
        return ""
    return " OR ".join(f'"{t}"' for t in tokens)


def retrieve_and_answer(
    video_id: str,
    question: str,
    language: str = "vi",
    top_k: int = 5,
) -> dict[str, Any]:
    t0 = time.time()

    fts_query = _build_fts_query(question)

    # Stage 1: FTS5 full-text search (skip if no usable tokens)
    with get_db() as conn:
        fts_rows = []
        if fts_query:
            fts_rows = conn.execute(
                """
                SELECT tm.*
                FROM Timeline_FTS fts
                JOIN Timeline_Metadata tm ON tm.id = fts.rowid
                WHERE fts.Timeline_FTS MATCH ?
                  AND tm.video_id = ?
                ORDER BY fts.rank
                LIMIT ?
                """,
                (fts_query, video_id, top_k),
            ).fetchall()

        if not fts_rows:
            # Fallback: grab first N segments ordered by timestamp
            fts_rows = conn.execute(
                """
                SELECT * FROM Timeline_Metadata
                WHERE video_id = ?
                ORDER BY timestamp_start
                LIMIT ?
                """,
                (video_id, top_k),
            ).fetchall()

    if not fts_rows:
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

    # Stage 2: Send candidates to Seed for reasoning
    segment_data = [
        {
            "timestamp_start": row["timestamp_start"],
            "timestamp_end": row["timestamp_end"],
            "transcript": row["transcript"],
            "ocr_text": row["ocr_text"],
            "audio_event": row["audio_event"],
            "detected_skus": row["detected_skus"],
        }
        for row in fts_rows
    ]

    best_segment = fts_rows[0]
    frame_paths: list[Path] = []
    fp = get_frame_path(video_id, best_segment["timestamp_start"])
    if fp:
        frame_paths.append(fp)

    seed_result = answer_question(
        segment_data=segment_data,
        question=question,
        language=language,
        frame_paths=frame_paths,
    )

    answer_ts = seed_result.get("timestamp") or best_segment["timestamp_start"]
    thumb = _thumbnail_url(video_id, float(answer_ts))

    total_ms = (time.time() - t0) * 1000
    return {
        "answer": seed_result.get("answer", ""),
        "timestamp": answer_ts,
        "timestamp_end": best_segment["timestamp_end"],
        "thumbnail_url": thumb,
        "reasoning_proof": seed_result.get("reasoning_proof", ""),
        "tokens_used": seed_result.get("_tokens", {"input": 0, "output": 0, "cache_read": 0}),
        "latency_ms": total_ms,
    }
