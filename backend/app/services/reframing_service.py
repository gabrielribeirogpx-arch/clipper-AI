from __future__ import annotations

from moviepy.video.fx.crop import crop

from app.services.face_tracking import analyze_clip_tracking_points
from app.services.motion_smoothing import FramingWindow, interpolate_window, smooth_windows


class ReframingService:
    """Auto-reframe horizontal videos to vertical 9:16 keeping main speaker centered."""

    def __init__(self, target_ratio=(9, 16), smooth_alpha: float = 0.28, sample_fps: float = 3.0):
        self.target_ratio = target_ratio
        self.smooth_alpha = smooth_alpha
        self.sample_fps = sample_fps

    def should_reframe(self, width: int, height: int) -> bool:
        return width > height

    def apply(self, clip):
        width = int(clip.w)
        height = int(clip.h)
        if not self.should_reframe(width, height):
            return clip

        target_w = int(height * (self.target_ratio[0] / self.target_ratio[1]))
        target_w = max(2, min(width, target_w))

        tracking = analyze_clip_tracking_points(clip, sample_fps=self.sample_fps)
        windows = [FramingWindow(time=p.time, center_x=p.center_x, center_y=p.center_y) for p in tracking]
        windows = smooth_windows(windows, alpha=self.smooth_alpha)

        def x1_at(t: float) -> float:
            win = interpolate_window(windows, float(t))
            center_x_px = win.center_x * width
            x1 = center_x_px - target_w / 2
            return max(0, min(width - target_w, x1))

        safe_top = int(height * 0.02)
        safe_bottom = int(height * 0.86)

        return crop(
            clip,
            x1=x1_at,
            y1=safe_top,
            x2=lambda t: x1_at(t) + target_w,
            y2=safe_bottom,
        ).resize((1080, 1920))
