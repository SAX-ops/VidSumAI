# backend/models.py
from pydantic import BaseModel
from typing import List, Optional


class FormatInfo(BaseModel):
    quality: str
    ext: str
    size: Optional[int] = None
    url: str


class VideoInfo(BaseModel):
    title: str
    thumbnail: str
    duration: Optional[int] = None
    formats: List[FormatInfo]


class ParseRequest(BaseModel):
    url: str


class DownloadTask(BaseModel):
    id: str
    url: str
    status: str = "pending"
    progress: float = 0.0
    filename: Optional[str] = None


class ProgressUpdate(BaseModel):
    percent: float
    speed: str
    eta: str
    downloaded: str
