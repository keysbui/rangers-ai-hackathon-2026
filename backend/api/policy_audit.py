from fastapi import APIRouter, HTTPException

from config import THUMBNAIL_DIR
from db import get_db
from models.query import PolicyAuditResponse, PolicyAuditSegment, PolicyViolation
from services.seed_client import policy_audit_segment

router = APIRouter(prefix="/api/policy-audit", tags=["policy-audit"])


def _thumb_url(video_id: str, ts: float) -> str | None:
    frame_idx = max(1, round(ts) + 1)
    p = THUMBNAIL_DIR / video_id / f"{frame_idx:06d}.jpg"
    return f"/thumbnails/{video_id}/{frame_idx:06d}.jpg" if p.exists() else None


@router.get("/{video_id}", response_model=PolicyAuditResponse)
def audit_video_policy(
    video_id: str,
    mode: str = "auto",
    start_ts: float | None = None,
    end_ts: float | None = None,
    limit: int = 200,
    min_confidence: float = 0.5,
    max_model_calls: int = 50,
):
    with get_db() as conn:
        row = conn.execute("SELECT status FROM Videos WHERE id=?", (video_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Video not found")
        if row["status"] != "done":
            raise HTTPException(status_code=409, detail="Video not fully processed yet")

        where = ["video_id=?"]
        params: list = [video_id]
        if start_ts is not None:
            where.append("timestamp_end >= ?")
            params.append(start_ts)
        if end_ts is not None:
            where.append("timestamp_start <= ?")
            params.append(end_ts)

        sql = f"SELECT * FROM Timeline_Metadata WHERE {' AND '.join(where)} ORDER BY timestamp_start LIMIT ?"
        params.append(limit)
        segments = conn.execute(sql, tuple(params)).fetchall()

    scanned_segments = len(segments)
    out_segments: list[PolicyAuditSegment] = []
    model_calls = 0
    total_violations = 0

    for seg in segments:
        transcript = seg["transcript"] or ""
        ocr_text = seg["ocr_text"] or ""
        detected_skus = seg["detected_skus"] or ""
        if not transcript and not ocr_text and not detected_skus:
            continue

        seg_mode = mode
        if seg_mode != "fast" and model_calls >= max_model_calls:
            seg_mode = "fast"

        result = policy_audit_segment(
            transcript=transcript,
            ocr_text=ocr_text,
            detected_skus=detected_skus,
            mode=seg_mode,
        )

        if result.get("_model_used"):
            model_calls += 1

        violations_raw = result.get("violations") or []
        violations: list[PolicyViolation] = []
        for v in violations_raw:
            if not isinstance(v, dict):
                continue
            try:
                conf = float(v.get("confidence", 0.0) or 0.0)
            except Exception:
                conf = 0.0
            if conf < min_confidence:
                continue
            violations.append(PolicyViolation(**v))

        if not violations:
            continue

        out_segments.append(
            PolicyAuditSegment(
                segment_id=seg["id"],
                timestamp_start=seg["timestamp_start"],
                timestamp_end=seg["timestamp_end"],
                thumbnail_url=_thumb_url(video_id, seg["timestamp_start"]),
                violations=violations,
            )
        )
        total_violations += len(violations)

    return PolicyAuditResponse(
        video_id=video_id,
        mode=mode,
        scanned_segments=scanned_segments,
        model_calls=model_calls,
        segments=out_segments,
        total_violations=total_violations,
    )

