from pydantic import BaseModel, Field


class YoutubeIngestRequest(BaseModel):
    youtube_url: str
    start_time: str | None = None
    end_time: str | None = None
    min_clip_length: int = Field(default=30, ge=10, le=300)
    max_clip_length: int = Field(default=90, ge=15, le=300)
