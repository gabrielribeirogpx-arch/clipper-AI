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


def get_timeline_state() -> dict[str, Any]:
    return timeline_state


def set_timeline_state(state: dict[str, Any]) -> None:
    timeline_state.clear()
    timeline_state.update(state)


def save_timeline_state_for_analysis(analysis_id: str | None, state: dict[str, Any]) -> None:
    normalized_analysis_id = str(analysis_id) if analysis_id is not None else None
    if not normalized_analysis_id:
        return

    print("[TIMELINE DB PRE-UPSERT]", {
        "analysis_id": normalized_analysis_id,
        "render_mode": state.get("render_mode"),
        "dual_region_config": state.get("dual_region_config"),
        "manual_region_config": state.get("manual_region"),
    })

    with SessionLocal() as session:
        row = session.get(TimelineRenderState, normalized_analysis_id)
        print(f"[TIMELINE DB ROW FOUND] analysis_id={normalized_analysis_id} found={row is not None}")
        if row is None:
            row = TimelineRenderState(analysis_id=normalized_analysis_id)
            print(f"[TIMELINE DB ROW CREATED] analysis_id={normalized_analysis_id}")

        row.render_mode = state.get("render_mode")
        row.dual_region_config = state.get("dual_region_config")
        row.manual_region_config = state.get("manual_region")

        session.add(row)
        session.flush()
        session.commit()
        session.refresh(row)

    print(f"[TIMELINE DB POST-COMMIT VERIFY] analysis_id={normalized_analysis_id}")
    with SessionLocal() as verify_session:
        verify_row = verify_session.get(TimelineRenderState, normalized_analysis_id)
        print("[TIMELINE DB VERIFIED VALUES]", {
            "analysis_id": normalized_analysis_id,
            "render_mode": verify_row.render_mode if verify_row else None,
            "dual_region_config": verify_row.dual_region_config if verify_row else None,
            "manual_region_config": verify_row.manual_region_config if verify_row else None,
        })


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
        hydrated["analysisId"] = normalized_analysis_id
        hydrated["render_mode"] = row.render_mode
        hydrated["dual_region_config"] = row.dual_region_config
        hydrated["dual_regions"] = row.dual_region_config
        hydrated["manual_region"] = row.manual_region_config

        print("[TIMELINE DB HYDRATION SUCCESS]", {
            "analysis_id": normalized_analysis_id,
            "render_mode": row.render_mode,
            "dual_region_config": row.dual_region_config,
            "manual_region_config": row.manual_region_config,
        })
        return hydrated
