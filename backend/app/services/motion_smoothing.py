from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class FramingWindow:
    time: float
    center_x: float
    center_y: float


def ease_in_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        return 4 * t * t * t
    return 1 - pow(-2 * t + 2, 3) / 2


def exponential_smooth(values: List[float], alpha: float = 0.35) -> List[float]:
    if not values:
        return []
    smoothed = [values[0]]
    for value in values[1:]:
        smoothed.append(alpha * value + (1 - alpha) * smoothed[-1])
    return smoothed


def smooth_windows(windows: List[FramingWindow], alpha: float = 0.35) -> List[FramingWindow]:
    if len(windows) <= 1:
        return windows

    xs = exponential_smooth([w.center_x for w in windows], alpha=alpha)
    ys = exponential_smooth([w.center_y for w in windows], alpha=alpha)

    result = []
    for i, win in enumerate(windows):
        result.append(FramingWindow(time=win.time, center_x=xs[i], center_y=ys[i]))
    return result


def interpolate_window(windows: List[FramingWindow], t: float) -> FramingWindow:
    if not windows:
        return FramingWindow(time=t, center_x=0.5, center_y=0.5)

    if t <= windows[0].time:
        return windows[0]
    if t >= windows[-1].time:
        return windows[-1]

    for i in range(len(windows) - 1):
        a = windows[i]
        b = windows[i + 1]
        if a.time <= t <= b.time:
            span = max(1e-6, b.time - a.time)
            local_t = ease_in_out_cubic((t - a.time) / span)
            return FramingWindow(
                time=t,
                center_x=a.center_x + (b.center_x - a.center_x) * local_t,
                center_y=a.center_y + (b.center_y - a.center_y) * local_t,
            )

    return windows[-1]
