from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import List, Tuple

import cv2
import numpy as np


@dataclass
class TrackingPoint:
    time: float
    center_x: float
    center_y: float
    confidence: float


@lru_cache(maxsize=1)
def _load_face_cascade() -> cv2.CascadeClassifier:
    return cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def _dominant_face(faces: np.ndarray) -> Tuple[int, int, int, int] | None:
    if faces is None or len(faces) == 0:
        return None
    areas = [w * h for (x, y, w, h) in faces]
    idx = int(np.argmax(areas))
    return tuple(int(v) for v in faces[idx])


def detect_primary_subject(frame: np.ndarray) -> Tuple[float, float, float]:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    cascade = _load_face_cascade()
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))

    face = _dominant_face(faces)
    h, w = frame.shape[:2]

    if face:
        x, y, fw, fh = face
        cx = (x + fw / 2.0) / w
        cy = (y + fh * 0.44) / h
        return cx, cy, 0.9

    # Fallback torso/body center bias: center-x and upper-middle y.
    return 0.5, 0.43, 0.25


def analyze_clip_tracking_points(clip, sample_fps: float = 3.0) -> List[TrackingPoint]:
    duration = max(0.0, float(clip.duration or 0.0))
    if duration <= 0:
        return [TrackingPoint(time=0.0, center_x=0.5, center_y=0.45, confidence=0.0)]

    points: List[TrackingPoint] = []
    step = max(1.0 / sample_fps, 0.12)
    t = 0.0

    while t < duration:
        frame_rgb = clip.get_frame(t)
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        cx, cy, conf = detect_primary_subject(frame_bgr)
        points.append(TrackingPoint(time=t, center_x=cx, center_y=cy, confidence=conf))
        t += step

    if not points or points[-1].time < duration:
        frame_rgb = clip.get_frame(max(0.0, duration - 1e-3))
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        cx, cy, conf = detect_primary_subject(frame_bgr)
        points.append(TrackingPoint(time=duration, center_x=cx, center_y=cy, confidence=conf))

    return points
