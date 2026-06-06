from __future__ import annotations

import time
from typing import Any
from db import get_db
from services.seed_client import rank_highlights
from services.frame_service import get_frame_path
from config import THUMBNAIL_DIR

DEFAULT_TRENDS = """
1. Flash Sale & Urgent Discounts: High energy, countdowns, and huge price drops.
2. Product Demo & ASMR: Clear close-ups of product features, satisfying sounds.
3. Authentic Reviews: Influencer or host showing genuine excitement and results.
4. Interactive Q&A: Host directly answering viewer comments or giving advice.
5. Vouchers & Giveaways: Highlighting promo codes, coupons, and free gifts.
"""

def _thumbnail_url(video_id: str, timestamp: float) -> str | None:
    frame_idx = max(1, round(timestamp) + 1)
    full = THUMBNAIL_DIR / video_id / f"{frame_idx:06d}.jpg"
    return f"/thumbnails/{video_id}/{frame_idx:06d}.jpg" if full.exists() else None

def get_trending_highlights(
    video_id: str,
    trends: str | None = None,
    language: str = "vi",
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Retrieve top segments and rank them based on trends for ad creation."""
    t0 = time.time()
    
    if not trends:
        trends = DEFAULT_TRENDS

    # Step 0: Check if we already have stored highlights for this video
    if not force_refresh:
        with get_db() as conn:
            stored = conn.execute(
                "SELECT * FROM Highlights WHERE video_id=? ORDER BY viral_score DESC",
                (video_id,)
            ).fetchall()
            if stored:
                highlights = [
                    {
                        "timestamp": row["timestamp_start"],
                        "timestamp_end": row["timestamp_end"],
                        "refined_start": row["refined_start"] if row["refined_start"] is not None else row["timestamp_start"],
                        "refined_end": row["refined_end"] if row["refined_end"] is not None else row["timestamp_end"],
                        "reason": row["reason"],
                        "ad_copy": row["ad_copy"],
                        "thumbnail_url": row["thumbnail_url"],
                        "energy_score": row["energy_score"],
                        "viral_score": row["viral_score"],
                    }
                    for row in stored
                ]
                return {
                    "highlights": highlights,
                    "trends_used": "Stored in database",
                    "tokens_used": {"input": 0, "output": 0, "cache_read": 0},
                    "latency_ms": (time.time() - t0) * 1000,
                }

    # Stage 1: Get top N segments by energy score as candidates
    with get_db() as conn:
        top_rows = conn.execute(
            """
            SELECT * FROM Timeline_Metadata
            WHERE video_id = ?
            ORDER BY energy_score DESC
            LIMIT 8
            """,
            (video_id,),
        ).fetchall()

    if not top_rows:
        return {"highlights": [], "latency_ms": (time.time() - t0) * 1000}

    # Fetch ALL segments for this video to provide full context to LLM
    with get_db() as conn:
        all_rows = conn.execute(
            "SELECT * FROM Timeline_Metadata WHERE video_id = ? ORDER BY timestamp_start",
            (video_id,)
        ).fetchall()

    segment_data = [
        {
            "timestamp_start": row["timestamp_start"],
            "timestamp_end": row["timestamp_end"],
            "transcript": row["transcript"],
            "ocr_text": row["ocr_text"],
            "audio_event": row["audio_event"],
            "detected_skus": row["detected_skus"],
            "energy_score": row["energy_score"],
        }
        for row in all_rows
    ]

    # Stage 2: Let Seed rank them and provide ad copy
    seed_result = rank_highlights(
        segment_data=segment_data,
        trends=trends,
        language=language,
    )

    highlights = []
    to_store = []
    for h in seed_result.get("highlights", []):
        ts = float(h.get("original_anchor", 0.0))
        # Find the original segment to get metadata for thumbnail
        original = next((s for s in segment_data if abs(s["timestamp_start"] - ts) < 0.1), None)
        
        # New refined timestamps from LLM - absolute values
        ref_start = float(h.get("refined_start", ts))
        ref_end = float(h.get("refined_end", ts + 15.0)) # Default 15s if missing
        
        # Enforce 120s limit and ensure logical order
        if ref_end <= ref_start:
            ref_end = ref_start + 15.0
        if ref_end - ref_start > 120:
            ref_end = ref_start + 120

        reason = h.get("reason", "")
        ad_copy = h.get("ad_copy", "")
        thumb = _thumbnail_url(video_id, ref_start) # Thumbnail at the exact start of highlight
        energy = original["energy_score"] if original else 0.0
        viral = float(h.get("viral_score", 0.0))

        highlights.append({
            "timestamp": ts, # keeping for anchor reference
            "timestamp_end": ref_end, # keeping for reference
            "refined_start": ref_start,
            "refined_end": ref_end,
            "reason": reason,
            "ad_copy": ad_copy,
            "thumbnail_url": thumb,
            "energy_score": energy,
            "viral_score": viral,
        })
        to_store.append((video_id, ts, ref_end, ref_start, ref_end, reason, ad_copy, thumb, energy, viral))

    # Sort by viral score descending
    highlights.sort(key=lambda x: x["viral_score"], reverse=True)

    # Stage 3: Store in database
    if to_store:
        with get_db() as conn:
            # Clear old ones if force_refresh
            if force_refresh:
                conn.execute("DELETE FROM Highlights WHERE video_id=?", (video_id,))
            
            conn.executemany(
                """
                INSERT INTO Highlights 
                    (video_id, timestamp_start, timestamp_end, refined_start, refined_end, 
                     reason, ad_copy, thumbnail_url, energy_score, viral_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                to_store
            )

    total_ms = (time.time() - t0) * 1000
    return {
        "highlights": highlights,
        "trends_used": trends,
        "tokens_used": seed_result.get("_tokens", {"input": 0, "output": 0, "cache_read": 0}),
        "latency_ms": total_ms,
    }
