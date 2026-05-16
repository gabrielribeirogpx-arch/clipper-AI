from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List


class CameraState(str, Enum):
    FOCUS_LEFT = "FOCUS_LEFT"
    FOCUS_RIGHT = "FOCUS_RIGHT"
    FOCUS_CENTER = "FOCUS_CENTER"
    DUAL_SPEAKER = "DUAL_SPEAKER"


@dataclass
class CameraStateEvent:
    time: float
    state: CameraState
    target_track_id: int | None


class CameraStateEngine:
    def __init__(self, min_focus_seconds: float = 2.0, min_speech_seconds: float = 0.7):
        self.min_focus_seconds = min_focus_seconds
        self.min_speech_seconds = min_speech_seconds
        self._current_state = CameraState.FOCUS_CENTER
        self._last_change_t = -999.0

    def resolve_state(self, t: float, face_x: float | None, has_dual: bool, speaker_duration: float) -> CameraState:
        if has_dual:
            return CameraState.DUAL_SPEAKER
        if face_x is None:
            return CameraState.FOCUS_CENTER
        if face_x < 0.42:
            return CameraState.FOCUS_LEFT
        if face_x > 0.58:
            return CameraState.FOCUS_RIGHT
        return CameraState.FOCUS_CENTER

    def update(self, t: float, proposed: CameraState, target_track_id: int | None, speaker_duration: float) -> CameraStateEvent:
        if speaker_duration < self.min_speech_seconds:
            proposed = self._current_state

        if proposed != self._current_state and (t - self._last_change_t) >= self.min_focus_seconds:
            self._current_state = proposed
            self._last_change_t = t

        return CameraStateEvent(time=t, state=self._current_state, target_track_id=target_track_id)


def build_speaker_segments(diarization_segments: List[dict]) -> List[dict]:
    clean = []
    for seg in diarization_segments:
        start = float(seg.get("start", 0.0) or 0.0)
        end = float(seg.get("end", start) or start)
        if end - start < 0.7:
            continue
        clean.append({"speaker": str(seg.get("speaker", "SPEAKER_00")), "start": start, "end": end})
    return clean
