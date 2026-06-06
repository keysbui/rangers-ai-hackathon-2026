from fastapi import APIRouter, HTTPException
from models.query import ComplianceResponse, ComplianceIssue
from services.seed_client import check_compliance
from services.frame_service import get_frame_path
from db import get_db
from config import THUMBNAIL_DIR

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


def _thumb_url(video_id: str, ts: float) -> str | None:
    frame_idx = max(1, round(ts) + 1)
    p = THUMBNAIL_DIR / video_id / f"{frame_idx:06d}.jpg"
    return f"/thumbnails/{video_id}/{frame_idx:06d}.jpg" if p.exists() else None


@router.get("/{video_id}", response_model=ComplianceResponse)
def check_video_compliance(video_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT status FROM Videos WHERE id=?", (video_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Video not found")
        if row["status"] != "done":
            raise HTTPException(status_code=409, detail="Video not fully processed yet")

        segments = conn.execute(
            "SELECT * FROM Timeline_Metadata WHERE video_id=? ORDER BY timestamp_start",
            (video_id,),
        ).fetchall()

    issues: list[ComplianceIssue] = []
    for seg in segments:
        transcript = seg["transcript"] or ""
        ocr_text = seg["ocr_text"] or ""
        if not transcript and not ocr_text:
            continue

        result = check_compliance(transcript, ocr_text)
        if result.get("has_issue"):
            issues.append(
                ComplianceIssue(
                    video_id=video_id,
                    timestamp_start=seg["timestamp_start"],
                    timestamp_end=seg["timestamp_end"],
                    transcript_claim=transcript,
                    ocr_text=ocr_text,
                    issue_description=result.get("issue_description", ""),
                    severity=result.get("severity", "low"),
                    thumbnail_url=_thumb_url(video_id, seg["timestamp_start"]),
                )
            )

    return ComplianceResponse(
        video_id=video_id,
        issues=issues,
        total_issues=len(issues),
    )
