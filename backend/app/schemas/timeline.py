from pydantic import BaseModel
from typing import List, Optional


class TimelineBlock(BaseModel):
    id: str
    label: str
    start: float
    end: float
    text: Optional[str] = None


class RenderStateResponse(BaseModel):
    duration: float
    current_time: float
    clips: List[TimelineBlock]
    reframing: List[TimelineBlock]
    cuts: List[TimelineBlock]


class TimelineUpdateRequest(BaseModel):
    subtitles: List[TimelineBlock]
    broll: List[TimelineBlock]
    hooks: List[TimelineBlock]
    cuts: List[TimelineBlock]
