from pydantic import BaseModel
from typing import List, Optional

class RegionBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class DualRegions(BaseModel):
    regionA: RegionBox
    regionB: RegionBox


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
    render_mode: Optional[str] = None
    dual_regions: Optional[DualRegions] = None
