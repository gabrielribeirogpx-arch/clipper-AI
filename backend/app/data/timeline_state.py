from __future__ import annotations

from typing import Any

from app.db import SessionLocal
from app.models.timeline_state_model import TimelineRenderState


timeline_state: dict[str, Any] = {
    "renderMode": "preview",
    "analysisId": None,
    "videoUrl": None,
    "previewVideoUrl": None,
    "exportVideoUrl": None,
    "duration": 0.0,
    "clips": [],
    "hooks": [],
    "broll": [],
    "cuts": [],
    "renderQueue": [],
    "render_mode": "ai_tracking",
    "dual_regions": None,
    "dual_region_config": None,
    "manual_region": None,
}

timeline_state_by_analysis: dict[str, dict[str, Any]] = {}


def get_timeline_state() -> dict[str, Any]:
    return timeline_state


def set_timeline_state(state: dict[str, Any]) -> None:
    timeline_state.clear()
    timeline_state.update(state)


def save_timeline_state_for_analysis(analysis_id: str | None, state: dict[str, Any]) -> None:
    if not analysis_id:
        return
    timeline_state_by_analysis[analysis_id] = dict(state)

    with SessionLocal() as session:
        row = session.get(TimelineRenderState, analysis_id)
        if row is None:
            row = TimelineRenderState(analysis_id=analysis_id)
            session.add(row)
        row.render_mode = state.get("render_mode")
        row.dual_region_config = state.get("dual_region_config")
        row.manual_region_config = state.get("manual_region")
        session.commit()
        session.refresh(row)
        print("[TIMELINE DB SAVE SUCCESS]", {
            "analysis_id": row.analysis_id,
            "render_mode": row.render_mode,
            "dual_region_config": row.dual_region_config,
            "manual_region_config": row.manual_region_config,
        })


def get_timeline_state_for_analysis(analysis_id: str | None) -> dict[str, Any] | None:
    if not analysis_id:
        return None
    saved = timeline_state_by_analysis.get(analysis_id)
    if saved:
        hydrated = dict(saved)
    else:
        hydrated = None

    with SessionLocal() as session:
        row = session.get(TimelineRenderState, analysis_id)
        if row:
            if hydrated is None:
                hydrated = dict(timeline_state)
                hydrated["analysisId"] = analysis_id
            hydrated["render_mode"] = row.render_mode
            hydrated["dual_region_config"] = row.dual_region_config
            hydrated["dual_regions"] = row.dual_region_config
            hydrated["manual_region"] = row.manual_region_config
            print("[TIMELINE DB LOAD SUCCESS]", {
                "analysis_id": row.analysis_id,
                "render_mode": row.render_mode,
                "dual_region_config": row.dual_region_config,
                "manual_region_config": row.manual_region_config,
            })
    return hydrated
