from __future__ import annotations

from typing import Any

from app.db import SessionLocal
from app.models.timeline_state_model import TimelineRenderState


# TODO(local-engine): this singleton keeps the current backend compatible, but it is risky for
# concurrent users/analyses. Move full timeline persistence to per-analysis_id storage
# before splitting the heavy local engine from the future cloud licensing/billing/sync API.
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
    "semi_auto": None,
    "semi_auto_config": None,
}


def get_timeline_state() -> dict[str, Any]:
    return timeline_state


def set_timeline_state(state: dict[str, Any]) -> None:
    timeline_state.clear()
    timeline_state.update(state)


def save_timeline_state_for_analysis(analysis_id: str | None, state: dict[str, Any]) -> None:
    normalized_analysis_id = str(analysis_id) if analysis_id is not None else None
    if not normalized_analysis_id:
        return

    print("[TIMELINE_SAVE_STARTED]", {
        "analysis_id": normalized_analysis_id,
        "clip_count": len(state.get("clips", [])),
        "render_mode": state.get("render_mode"),
    })

    try:
        with SessionLocal() as session:
            row = session.get(TimelineRenderState, normalized_analysis_id)
            if row is None:
                row = TimelineRenderState(analysis_id=normalized_analysis_id)

            row.render_mode = state.get("render_mode")
            row.dual_region_config = state.get("dual_region_config")
            row.semi_auto_config = state.get("semi_auto_config", state.get("semi_auto"))
            row.state_json = dict(state)

            session.add(row)
            session.commit()

        print("[TIMELINE_SAVE_SUCCESS]", {
            "analysis_id": normalized_analysis_id,
            "clip_count": len(state.get("clips", [])),
            "render_mode": state.get("render_mode"),
        })
    except Exception as error:
        print("[TIMELINE_SAVE_FAILED]", {
            "analysis_id": normalized_analysis_id,
            "error": str(error),
        })
        raise

def get_timeline_state_for_analysis(analysis_id: str | None) -> dict[str, Any] | None:
    normalized_analysis_id = str(analysis_id) if analysis_id is not None else None
    if not normalized_analysis_id:
        return None

    with SessionLocal() as session:
        row = session.get(TimelineRenderState, normalized_analysis_id)
        if row is None:
            print(f"[TIMELINE DB LOAD MISS] analysis_id={normalized_analysis_id}")
            return None

        hydrated = dict(timeline_state)
        if row.state_json:
            hydrated.update(row.state_json)
        hydrated["analysisId"] = normalized_analysis_id
        hydrated["render_mode"] = row.render_mode or hydrated.get("render_mode")
        hydrated["dual_region_config"] = row.dual_region_config or hydrated.get("dual_region_config")
        hydrated["dual_regions"] = hydrated.get("dual_region_config")
        hydrated["semi_auto"] = row.semi_auto_config or hydrated.get("semi_auto_config") or hydrated.get("semi_auto")
        hydrated["semi_auto_config"] = hydrated.get("semi_auto")

        print("[TIMELINE_LOAD_SUCCESS]", {
            "analysis_id": normalized_analysis_id,
            "clip_count": len(hydrated.get("clips", [])),
            "render_mode": hydrated.get("render_mode"),
        })
        return hydrated
