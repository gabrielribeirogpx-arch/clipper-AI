from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Dict, List

from moviepy.editor import VideoFileClip

from app.services.reframing_service import ReframingService

SAFE_CPU_RENDER = os.getenv("SAFE_CPU_RENDER", "false").strip().lower() in {"1", "true", "yes", "on"}
MAX_TRACKING_WIDTH = 1920
TARGET_RENDER_SIZE = (1080, 1920)


def _probe_dimensions(media_path: str) -> tuple[int, int]:
    probe_cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", media_path,
    ]
    proc = subprocess.run(probe_cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Failed to probe video dimensions for {media_path}: {proc.stderr}")
    w, h = (proc.stdout or "").strip().split("x", 1)
    return int(w), int(h)


def _create_proxy_if_needed(video_path: str) -> tuple[str, bool]:
    width, _ = _probe_dimensions(video_path)
    if width <= MAX_TRACKING_WIDTH:
        return video_path, False

    proxy_file = tempfile.NamedTemporaryFile(prefix="proxy_1080_", suffix=".mp4", delete=False)
    proxy_file.close()
    proxy_path = proxy_file.name
    cmd = [
        "ffmpeg", "-y", "-i", video_path, "-vf", "scale=1920:-2",
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-an", proxy_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Failed to create proxy video.\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    return proxy_path, True


def render_vertical_clip(video_path: str, segments: List[Dict], output_path: str, speaker_segments=None) -> str:
    """Render a vertical clip with camera reframing and original audio, without subtitles."""
    tracking_source, proxy_created = _create_proxy_if_needed(video_path)
    tracking_clip = VideoFileClip(tracking_source)

    sample_fps = 4.0 if SAFE_CPU_RENDER else 6.0
    max_zoom = 1.08 if SAFE_CPU_RENDER else 1.12
    reframer = ReframingService(sample_fps=sample_fps, max_zoom=max_zoom)

    reframed_video = reframer.apply(VideoFileClip(video_path).without_audio())
    final_video = reframed_video.set_audio(VideoFileClip(video_path).audio)

    final_video.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        fps=30,
        preset="medium",
    )

    final_w, final_h = _probe_dimensions(output_path)
    if (final_w, final_h) != TARGET_RENDER_SIZE:
        raise RuntimeError(f"Rendered video has invalid size {final_w}x{final_h}; expected 1080x1920")

    if proxy_created and tracking_source != video_path and os.path.exists(tracking_source):
        tracking_clip.close()
        try:
            os.remove(tracking_source)
        except PermissionError:
            print(f"[WARN] could not delete proxy: {tracking_source}")

    return output_path
