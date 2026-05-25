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
    normalized_analysis_id = str(analysis_id) if analysis_id is not None else None
    if not normalized_analysis_id:
        return
    timeline_state_by_analysis[normalized_analysis_id] = dict(state)

    print("[TIMELINE DB UPSERT]", {
        "analysis_id": normalized_analysis_id,
        "incoming_render_mode": state.get("render_mode"),
        "incoming_dual_region_config": state.get("dual_region_config"),
        "incoming_manual_region_config": state.get("manual_region"),
    })

    with SessionLocal() as session:
        row = session.get(TimelineRenderState, normalized_analysis_id)
        if row is None:
            row = TimelineRenderState(analysis_id=normalized_analysis_id)
            session.add(row)
            print(f"[TIMELINE DB ROW CREATED] analysis_id={normalized_analysis_id}")
        else:
            print(f"[TIMELINE DB ROW UPDATED] analysis_id={normalized_analysis_id}")

        row.render_mode = state.get("render_mode")
        row.dual_region_config = state.get("dual_region_config")
        row.manual_region_config = state.get("manual_region")

        session.flush()
        print(f"[TIMELINE DB FLUSH SUCCESS] analysis_id={normalized_analysis_id}")

        session.commit()
        print(f"[TIMELINE DB COMMIT SUCCESS] analysis_id={normalized_analysis_id}")

        session.refresh(row)
        print(f"[TIMELINE DB REFRESH SUCCESS] analysis_id={normalized_analysis_id}")

        verify_row = session.get(TimelineRenderState, normalized_analysis_id)
        print("[TIMELINE DB VERIFY]", {
            "analysis_id": row.analysis_id,
            "persisted_render_mode": verify_row.render_mode if verify_row else None,
            "persisted_dual_region_config": verify_row.dual_region_config if verify_row else None,
            "persisted_manual_region_config": verify_row.manual_region_config if verify_row else None,
        })


def get_timeline_state_for_analysis(analysis_id: str | None) -> dict[str, Any] | None:
    normalized_analysis_id = str(analysis_id) if analysis_id is not None else None
    if not normalized_analysis_id:
        return None
    saved = timeline_state_by_analysis.get(normalized_analysis_id)
    if saved:
        hydrated = dict(saved)
    else:
        hydrated = None

    with SessionLocal() as session:
        row = session.get(TimelineRenderState, normalized_analysis_id)
        if row:
            if hydrated is None:
                hydrated = dict(timeline_state)
                hydrated["analysisId"] = normalized_analysis_id
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
    if hydrated is None:
        print(f"[TIMELINE DB LOAD MISS] analysis_id={normalized_analysis_id}")
    return hydrated
