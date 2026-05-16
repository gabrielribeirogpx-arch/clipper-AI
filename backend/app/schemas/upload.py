from pydantic import BaseModel, Field


class YoutubeIngestRequest(BaseModel):
    youtube_url: str
    start_time: str | None = None
    end_time: str | None = None
    min_clip_length: int = Field(default=30, ge=10, le=300)
    max_clip_length: int = Field(default=90, ge=15, le=300)
    max_clips: int = Field(default=25, ge=1, le=200)
    min_score: float = Field(default=0.45, ge=0.0, le=1.0)
    overlap_tolerance: float = Field(default=0.6, ge=0.0, le=1.0)
