from __future__ import annotations

from typing import Dict, List

import cv2
from moviepy.video.fx.crop import crop

from app.services.camera_state_engine import CameraStateEngine, build_speaker_segments
from app.services.multi_face_tracker import MultiFaceTracker
from app.services.speaker_focus_service import SpeakerFocusService


class ReframingService:
    def __init__(self, target_ratio=(9, 16), sample_fps: float = 4.0, min_zoom: float = 1.0, max_zoom: float = 1.12):
        self.target_ratio = target_ratio
        self.sample_fps = sample_fps
        self.min_zoom = min_zoom
        self.max_zoom = max_zoom
        self.camera_keyframes: List[Dict] = []

    def should_reframe(self, width: int, height: int) -> bool:
        return width > height

    def _speaker_at(self, t: float, speaker_segments: List[Dict]) -> str:
        for seg in speaker_segments:
            if float(seg["start"]) <= t <= float(seg["end"]):
                return str(seg["speaker"])
        return "SPEAKER_00"

    def apply(self, clip, speaker_segments: List[Dict] | None = None, debug: bool = False):
        width = int(clip.w)
        height = int(clip.h)
        if not self.should_reframe(width, height):
            return clip

        target_w = int(height * (self.target_ratio[0] / self.target_ratio[1]))
        target_w = max(2, min(width, target_w))
        duration = float(clip.duration or 0.0)

        tracker = MultiFaceTracker()
        focus_service = SpeakerFocusService(switch_cooldown=1.0)
        state_engine = CameraStateEngine(min_focus_seconds=2.0, min_speech_seconds=0.7)
        speaker_segments = build_speaker_segments(speaker_segments or [])

        frame_plan = []
        step = max(0.2, 1.0 / self.sample_fps)
        t = 0.0
        while t <= duration:
            frame = cv2.cvtColor(clip.get_frame(t), cv2.COLOR_RGB2BGR)
            tracks = tracker.update(frame, t)
            active_speaker = self._speaker_at(t, speaker_segments)
            decision = focus_service.choose_focus(t, active_speaker, tracks)
            selected = next((x for x in tracks if decision and x.track_id == decision.track_id), None)
            seg_len = 0.8
            for seg in speaker_segments:
                if seg["speaker"] == active_speaker and seg["start"] <= t <= seg["end"]:
                    seg_len = seg["end"] - seg["start"]
            state = state_engine.resolve_state(t, selected.smooth_center_x if selected else None, len(tracks) > 1, seg_len)
            state_event = state_engine.update(t, state, selected.track_id if selected else None, seg_len)
            center_x = selected.smooth_center_x if selected else 0.5
            zoom = min(self.max_zoom, max(self.min_zoom, 1.02 + (0.05 if selected else 0.0)))
            frame_plan.append({"t": t, "center_x": center_x, "zoom": zoom, "state": state_event.state.value})
            t += step

        self.camera_keyframes = [
            {"t": p["t"], "target": p["state"].lower(), "zoom": round(float(p["zoom"]), 3)}
            for p in frame_plan
        ]

        # Keep compatibility: stable center crop but now speaker-aware planning is available.
        avg_center_x = sum(p["center_x"] for p in frame_plan) / max(1, len(frame_plan))
        x_center_px = int(avg_center_x * width)
        half = target_w // 2
        x1 = max(0, min(width - target_w, x_center_px - half))
        x2 = x1 + target_w

        reframed = crop(clip, x1=x1, x2=x2, y1=0, y2=height).resize((1080, 1920))
        return reframed.set_audio(clip.audio)
