from __future__ import annotations

from moviepy.video.fx.crop import crop


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

        x1 = max((width - target_w) // 2, 0)
        x2 = x1 + target_w

        reframed = crop(
            clip,
            x1=x1,
            x2=x2,
            y1=0,
            y2=height,
        ).resize((1080, 1920))

        return reframed.set_audio(clip.audio)
