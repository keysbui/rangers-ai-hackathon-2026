from pydantic import BaseModel, HttpUrl
from typing import Optional
from enum import Enum


class VideoStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    error = "error"


class VideoCreate(BaseModel):
    url: Optional[str] = None


class VideoResponse(BaseModel):
    id: str
    name: str
    url: Optional[str]
    duration: Optional[float]
    status: VideoStatus
    created_at: str


class VideoSummaryResponse(BaseModel):
    video_id: str
    language: str
    overview: str
    product_details: str
