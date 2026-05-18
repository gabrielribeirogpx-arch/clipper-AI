from __future__ import annotations

from typing import Any


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


def get_timeline_state_for_analysis(analysis_id: str | None) -> dict[str, Any] | None:
    if not analysis_id:
        return None
    saved = timeline_state_by_analysis.get(analysis_id)
    return dict(saved) if saved else None
