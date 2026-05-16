from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from app.services.multi_face_tracker import FaceTrack


@dataclass
class FocusDecision:
    time: float
    speaker: str
    track_id: int
    score: float


class SpeakerFocusService:
    def __init__(self, switch_cooldown: float = 1.0):
        self.switch_cooldown = switch_cooldown
        self._last_track_id: Optional[int] = None
        self._last_switch_time: float = -999.0

    def choose_focus(self, t: float, active_speaker: str, tracks: List[FaceTrack]) -> Optional[FocusDecision]:
        if not tracks:
            return None

        scores: Dict[int, float] = {}
        for track in tracks:
            center_bias = 1.0 - min(1.0, abs(track.smooth_center_x - 0.5) * 2.0)
            motion_bias = min(1.0, track.motion_score * 25.0)
            persistence = min(1.0, len(track.timestamps) / 12.0)
            conf = track.confidence
            score = (0.4 * center_bias) + (0.25 * motion_bias) + (0.2 * persistence) + (0.15 * conf)
            if self._last_track_id == track.track_id:
                score += 0.08
            scores[track.track_id] = score

        best_id = max(scores, key=scores.get)

        if self._last_track_id is not None and best_id != self._last_track_id and (t - self._last_switch_time) < self.switch_cooldown:
            best_id = self._last_track_id

        if best_id != self._last_track_id:
            self._last_switch_time = t
            self._last_track_id = best_id

        return FocusDecision(time=t, speaker=active_speaker, track_id=best_id, score=scores.get(best_id, 0.0))
