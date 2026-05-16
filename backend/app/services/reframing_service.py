from __future__ import annotations

from typing import Dict, List

import cv2
import numpy as np

from app.services.camera_state_engine import CameraStateEngine, build_speaker_segments
from app.services.multi_face_tracker import MultiFaceTracker
from app.services.speaker_focus_service import SpeakerFocusService


class ReframingService:
    def __init__(self, target_ratio=(9, 16), sample_fps: float = 6.0, min_zoom: float = 1.0, max_zoom: float = 1.12):
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
        duration = float(clip.duration or 0.0)

        out_size = (1080, 1920)
        if not self.should_reframe(width, height):
            return clip.resize(out_size)

        base_crop_w = int(height * (self.target_ratio[0] / self.target_ratio[1]))
        base_crop_w = max(2, min(width, base_crop_w))

        tracker = MultiFaceTracker()
        focus_service = SpeakerFocusService(switch_cooldown=1.2)
        state_engine = CameraStateEngine(min_focus_seconds=2.0, min_speech_seconds=0.7)
        speaker_segments = build_speaker_segments(speaker_segments or [])

        frame_plan = []
        step = max(0.12, 1.0 / self.sample_fps)
        t = 0.0
        smooth_x = 0.5
        vel_x = 0.0
        smooth_zoom = 1.0

        while t <= duration + 1e-6:
            frame = cv2.cvtColor(clip.get_frame(t), cv2.COLOR_RGB2BGR)
            tracks = tracker.update(frame, t)
            active_speaker = self._speaker_at(t, speaker_segments)
            decision = focus_service.choose_focus(t, active_speaker, tracks)
            selected = next((x for x in tracks if decision and x.track_id == decision.track_id), None)

            seg_len = 0.8
            for seg in speaker_segments:
                if seg["speaker"] == active_speaker and seg["start"] <= t <= seg["end"]:
                    seg_len = seg["end"] - seg["start"]
                    break

            state = state_engine.resolve_state(t, selected.smooth_center_x if selected else None, len(tracks) > 1, seg_len)
            state_event = state_engine.update(t, state, selected.track_id if selected else None, seg_len)

            target_x = selected.smooth_center_x if selected else 0.5
            target_zoom = 1.02
            if selected:
                # Faces menores -> mais zoom, com limite sutil
                fw = max(1, selected.bbox[2])
                relative_face = fw / max(1, width)
                target_zoom += max(0.0, min(0.1, (0.23 - relative_face) * 0.45))

            target_zoom = min(self.max_zoom, max(self.min_zoom, target_zoom))

            # inertia + dampening
            dt = step
            stiffness = 7.0
            damping = 0.86
            force = (target_x - smooth_x) * stiffness
            vel_x = (vel_x + force * dt) * damping
            smooth_x += vel_x * dt
            smooth_x = max(0.0, min(1.0, smooth_x))

            zoom_alpha = min(1.0, dt * 3.0)
            smooth_zoom = smooth_zoom + (target_zoom - smooth_zoom) * zoom_alpha

            frame_plan.append({
                "t": round(t, 3),
                "center_x": float(smooth_x),
                "zoom": float(smooth_zoom),
                "target_center_x": float(target_x),
                "state": state_event.state.value,
                "speaker": active_speaker,
                "track_id": int(selected.track_id) if selected else None,
            })
            t += step

        if not frame_plan:
            frame_plan = [{"t": 0.0, "center_x": 0.5, "zoom": 1.0, "state": "FOCUS_CENTER", "speaker": "SPEAKER_00", "track_id": None}]

        self.camera_keyframes = frame_plan

        times = np.array([p["t"] for p in frame_plan], dtype=np.float32)
        centers = np.array([p["center_x"] for p in frame_plan], dtype=np.float32)
        zooms = np.array([p["zoom"] for p in frame_plan], dtype=np.float32)

        def _interp(ti: float):
            c = float(np.interp(ti, times, centers))
            z = float(np.interp(ti, times, zooms))
            return c, z

        def _crop_frame(get_frame, t_frame: float):
            frame = get_frame(t_frame)
            c, z = _interp(float(t_frame))
            crop_w = max(2, min(width, int(base_crop_w / max(1e-4, z))))
            half = crop_w // 2
            x_center_px = int(c * width)
            x1 = max(0, min(width - crop_w, x_center_px - half))
            x2 = x1 + crop_w
            out = frame[:, x1:x2]

            if debug:
                dbg = out.copy()
                cv2.rectangle(dbg, (0, 0), (dbg.shape[1] - 1, dbg.shape[0] - 1), (0, 255, 255), 3)
                label = f"spk={next((k['speaker'] for k in reversed(frame_plan) if k['t'] <= t_frame), 'NA')} z={z:.3f} x={c:.3f}"
                cv2.putText(dbg, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2, cv2.LINE_AA)
                out = dbg
            return out

        reframed = clip.fl(_crop_frame, apply_to=["mask"]).resize(out_size)
        return reframed.set_audio(clip.audio)
