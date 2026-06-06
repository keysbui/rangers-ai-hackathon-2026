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


class PolicyViolation(BaseModel):
    rule_id: str
    rule_name: str
    policy_category: str
    severity: str
    confidence: float
    evidence: dict


class PolicyAuditSegment(BaseModel):
    segment_id: int
    timestamp_start: float
    timestamp_end: float
    thumbnail_url: Optional[str]
    violations: list[PolicyViolation]


class PolicyAuditResponse(BaseModel):
    video_id: str
    mode: str
    scanned_segments: int
    model_calls: int
    segments: list[PolicyAuditSegment]
    total_violations: int


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
