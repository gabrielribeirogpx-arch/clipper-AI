from __future__ import annotations

from typing import Any


timeline_state: dict[str, Any] = {
    "renderMode": "preview",
    "videoUrl": None,
    "previewVideoUrl": None,
    "exportVideoUrl": None,
    "duration": 0.0,
    "clips": [],
    "subtitles": [],
    "hooks": [],
    "broll": [],
    "cuts": [],
}


def get_timeline_state() -> dict[str, Any]:
    return timeline_state


def set_timeline_state(state: dict[str, Any]) -> None:
    timeline_state.clear()
    timeline_state.update(state)
