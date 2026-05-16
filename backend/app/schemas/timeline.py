from pydantic import BaseModel
from typing import List, Optional


class TimelineBlock(BaseModel):
    id: str
    label: str
    start: float
    end: float
    text: Optional[str] = None


class RenderStateResponse(BaseModel):
    videoUrl: Optional[str] = None
    duration: float
    clips: List[TimelineBlock]
    hooks: List[TimelineBlock]
    broll: List[TimelineBlock]
    cuts: List[TimelineBlock]


class TimelineUpdateRequest(BaseModel):
    broll: List[TimelineBlock]
    hooks: List[TimelineBlock]
    cuts: List[TimelineBlock]
