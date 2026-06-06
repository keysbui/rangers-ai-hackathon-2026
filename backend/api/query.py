from fastapi import APIRouter, HTTPException
from models.query import QueryRequest, QueryResponse
from services.retrieval import retrieve_and_answer
from db import get_db

router = APIRouter(prefix="/api/query", tags=["query"])


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
    return QueryResponse(**result)
