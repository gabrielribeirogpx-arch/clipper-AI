from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Tuple

import cv2
import numpy as np


@dataclass
class FaceTrack:
    track_id: int
    bbox: Tuple[int, int, int, int]
    confidence: float
    center_x: float
    center_y: float
    start_time: float
    last_seen: float
    timestamps: List[float] = field(default_factory=list)
    miss_count: int = 0
    smooth_center_x: float = 0.5
    smooth_center_y: float = 0.45
    motion_score: float = 0.0


@lru_cache(maxsize=1)
def _load_face_cascade() -> cv2.CascadeClassifier:
    return cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


class MultiFaceTracker:
    def __init__(self, max_distance_px: float = 120.0, max_missed_frames: int = 8, smoothing_alpha: float = 0.42):
        self.max_distance_px = max_distance_px
        self.max_missed_frames = max_missed_frames
        self.smoothing_alpha = smoothing_alpha
        self._tracks: Dict[int, FaceTrack] = {}
        self._next_id = 1

    def detect_faces(self, frame: np.ndarray):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cascade = _load_face_cascade()
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
        return [tuple(int(v) for v in face) for face in (faces if faces is not None else [])]

    def _distance(self, center_a: Tuple[float, float], center_b: Tuple[float, float]) -> float:
        return float(np.hypot(center_a[0] - center_b[0], center_a[1] - center_b[1]))

    def update(self, frame: np.ndarray, t: float) -> List[FaceTrack]:
        h, w = frame.shape[:2]
        faces = self.detect_faces(frame)
        detections = []
        for (x, y, fw, fh) in faces:
            cx = x + fw / 2.0
            cy = y + fh * 0.45
            confidence = max(0.3, min(0.98, (fw * fh) / max(1.0, w * h) * 24.0))
            detections.append({"bbox": (x, y, fw, fh), "center": (cx, cy), "confidence": confidence})

        unmatched_tracks = set(self._tracks.keys())
        for det in detections:
            chosen_id = None
            chosen_dist = 10e9
            for track_id in list(unmatched_tracks):
                track = self._tracks[track_id]
                dist = self._distance(det["center"], (track.smooth_center_x * w, track.smooth_center_y * h))
                if dist < chosen_dist and dist <= self.max_distance_px:
                    chosen_id = track_id
                    chosen_dist = dist

            if chosen_id is None:
                track_id = self._next_id
                self._next_id += 1
                x, y, fw, fh = det["bbox"]
                self._tracks[track_id] = FaceTrack(
                    track_id=track_id,
                    bbox=det["bbox"],
                    confidence=det["confidence"],
                    center_x=det["center"][0] / w,
                    center_y=det["center"][1] / h,
                    smooth_center_x=det["center"][0] / w,
                    smooth_center_y=det["center"][1] / h,
                    start_time=t,
                    last_seen=t,
                    timestamps=[t],
                )
                continue

            track = self._tracks[chosen_id]
            x, y, fw, fh = det["bbox"]
            new_cx = det["center"][0] / w
            new_cy = det["center"][1] / h
            track.motion_score = 0.8 * track.motion_score + 0.2 * self._distance((track.center_x, track.center_y), (new_cx, new_cy))
            track.center_x = new_cx
            track.center_y = new_cy
            track.smooth_center_x = self.smoothing_alpha * new_cx + (1 - self.smoothing_alpha) * track.smooth_center_x
            track.smooth_center_y = self.smoothing_alpha * new_cy + (1 - self.smoothing_alpha) * track.smooth_center_y
            track.bbox = (x, y, fw, fh)
            track.confidence = max(track.confidence * 0.75, det["confidence"])
            track.last_seen = t
            track.timestamps.append(t)
            track.miss_count = 0
            unmatched_tracks.discard(chosen_id)

        expired = []
        for track_id, track in self._tracks.items():
            if track.last_seen < t:
                track.miss_count += 1
            if track.miss_count > self.max_missed_frames:
                expired.append(track_id)

        for track_id in expired:
            del self._tracks[track_id]

        return list(self._tracks.values())
