from pydantic import BaseModel
from typing import Optional


class TimelineSegment(BaseModel):
    id: int
    video_id: str
    timestamp_start: float
    timestamp_end: float
    transcript: Optional[str]
    ocr_text: Optional[str]
    audio_event: Optional[str]
    detected_skus: Optional[str]
    energy_score: float
    thumbnail_url: Optional[str]
