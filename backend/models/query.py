from pydantic import BaseModel
from typing import Optional


class QueryRequest(BaseModel):
    video_id: str
    question: str
    language: str = "vi"


class QueryResponse(BaseModel):
    answer: str
    timestamp: Optional[float]
    timestamp_end: Optional[float]
    thumbnail_url: Optional[str]
    reasoning_proof: str
    tokens_used: dict
    latency_ms: float


class ComplianceIssue(BaseModel):
    video_id: str
    timestamp_start: float
    timestamp_end: float
    transcript_claim: str
    ocr_text: str
    issue_description: str
    severity: str
    thumbnail_url: Optional[str]


class ComplianceResponse(BaseModel):
    video_id: str
    issues: list[ComplianceIssue]
    total_issues: int


class QAHistoryItem(BaseModel):
    id: int
    video_id: str
    question: str
    language: str
    answer: str
    timestamp: Optional[float]
    timestamp_end: Optional[float]
    thumbnail_url: Optional[str]
    reasoning_proof: str
    tokens_used: dict
    latency_ms: Optional[float]
    created_at: str
