import logging

from fastapi import APIRouter, HTTPException
from models.query import QueryRequest, QueryResponse, QAHistoryItem
from services.retrieval import retrieve_and_answer
from db import get_db

logger = logging.getLogger("query")

router = APIRouter(prefix="/api/query", tags=["query"])


def _row_to_history_item(row) -> QAHistoryItem:
    return QAHistoryItem(
        id=row["id"],
        video_id=row["video_id"],
        question=row["question"],
        language=row["language"],
        answer=row["answer"] or "",
        timestamp=row["timestamp"],
        timestamp_end=row["timestamp_end"],
        thumbnail_url=row["thumbnail_url"],
        reasoning_proof=row["reasoning_proof"] or "",
        tokens_used={
            "input": row["tokens_input"] or 0,
            "output": row["tokens_output"] or 0,
            "cache_read": row["tokens_cache_read"] or 0,
        },
        latency_ms=row["latency_ms"],
        created_at=row["created_at"],
    )


@router.post("", response_model=QueryResponse)
def query_video(req: QueryRequest):
    with get_db() as conn:
        row = conn.execute("SELECT status FROM Videos WHERE id=?", (req.video_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Video not found")
    if row["status"] not in ("done",):
        raise HTTPException(
            status_code=409,
            detail=f"Video is not ready (status={row['status']}). Wait for processing to finish.",
        )

    result = retrieve_and_answer(
        video_id=req.video_id,
        question=req.question,
        language=req.language,
    )

    # Persist to QA_History (best-effort: never break the QA response on failure)
    try:
        tokens = result.get("tokens_used", {})
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO QA_History
                    (video_id, question, language, answer, timestamp, timestamp_end,
                     thumbnail_url, reasoning_proof,
                     tokens_input, tokens_output, tokens_cache_read, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    req.video_id,
                    req.question,
                    req.language,
                    result.get("answer", ""),
                    result.get("timestamp"),
                    result.get("timestamp_end"),
                    result.get("thumbnail_url"),
                    result.get("reasoning_proof", ""),
                    tokens.get("input", 0),
                    tokens.get("output", 0),
                    tokens.get("cache_read", 0),
                    result.get("latency_ms"),
                ),
            )
    except Exception as exc:
        logger.warning("Failed to save QA history: %s", exc)

    return QueryResponse(**result)


@router.get("/history/{video_id}", response_model=list[QAHistoryItem])
def get_qa_history(video_id: str):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM QA_History WHERE video_id=? ORDER BY created_at ASC, id ASC",
            (video_id,),
        ).fetchall()
    return [_row_to_history_item(r) for r in rows]
