from pydantic import BaseModel
from typing import List, Literal, Optional


class TimelineBlock(BaseModel):
    id: str
    label: str
    start: float
    end: float
    text: Optional[str] = None
    caption_position: Literal["top", "middle", "bottom"] = "bottom"
    caption_preset: Literal["cinematic", "tiktok", "hormozi", "minimal", "neon"] = "cinematic"


class RenderStateResponse(BaseModel):
    videoUrl: Optional[str] = None
    duration: float
    clips: List[TimelineBlock]
    subtitles: List[TimelineBlock]
    hooks: List[TimelineBlock]
    broll: List[TimelineBlock]
    cuts: List[TimelineBlock]


class TimelineUpdateRequest(BaseModel):
    subtitles: List[TimelineBlock]
    broll: List[TimelineBlock]
    hooks: List[TimelineBlock]
    cuts: List[TimelineBlock]
