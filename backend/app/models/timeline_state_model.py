from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TimelineRenderState(Base):
    __tablename__ = "timeline_render_state"

    analysis_id: Mapped[str] = mapped_column(String, primary_key=True)
    render_mode: Mapped[str | None] = mapped_column(String, nullable=True)
    dual_region_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    manual_region_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

