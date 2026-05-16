from __future__ import annotations

import os
import math
import re
import subprocess
import tempfile
from typing import Dict, List

from moviepy.editor import CompositeVideoClip, VideoFileClip

from app.services.reframing_service import ReframingService
from app.services.subtitle_renderer import SubtitleRenderer

os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
SAFE_CPU_RENDER = os.getenv("SAFE_CPU_RENDER", "false").strip().lower() in {"1", "true", "yes", "on"}
MAX_TRACKING_WIDTH = 1920
TARGET_RENDER_SIZE = (1080, 1920)


IMPACT_KEYWORDS = {
    "agora", "nunca", "sempre", "urgente", "segredo", "choque", "chocante",
    "bomba", "explodiu", "verdade", "imediato", "proibido", "erro", "absurdo",
}

PUNCHLINE_PHRASES = (
    "moral da história", "resumo", "conclusão", "resultado", "a verdade é",
    "e é por isso", "no final", "só que", "plot twist",
)


def _normalize_word(word: str) -> str:
    return re.sub(r"[^\wÀ-ÿ]", "", (word or "").strip().lower())


def _collect_zoom_events(words: List[Dict]) -> List[Dict]:
    events: List[Dict] = []
    for idx, word_data in enumerate(words):
        if "start" not in word_data or "end" not in word_data:
            continue

        raw_word = str(word_data.get("word", "")).strip()
        if not raw_word:
            continue

        start = float(word_data["start"])
        end = float(word_data["end"])
        duration = max(0.06, end - start)
        norm = _normalize_word(raw_word)

        is_shout = (raw_word.isupper() and len(raw_word) >= 3) or ("!" in raw_word)
        has_impact_keyword = norm in IMPACT_KEYWORDS

        context = " ".join(str(words[j].get("word", "")).lower() for j in range(max(0, idx - 3), min(len(words), idx + 4)))
        has_punchline = any(phrase in context for phrase in PUNCHLINE_PHRASES)

        intensity = 0.0
        if has_impact_keyword:
            intensity += 0.42
        if is_shout:
            intensity += 0.38
        if has_punchline:
            intensity += 0.32

        lookback = [w for w in words[max(0, idx - 6): idx + 1] if "start" in w]
        if len(lookback) >= 3:
            span = max(0.25, float(lookback[-1]["start"]) - float(lookback[0]["start"]))
            local_wps = len(lookback) / span
            emotional_ramp = max(0.0, min(1.0, (local_wps - 2.6) / 2.2))
            intensity += 0.35 * emotional_ramp

        intensity = max(0.0, min(1.0, intensity))
        if intensity < 0.24:
            continue

        events.append({
            "start": start,
            "peak": start + duration * 0.45,
            "end": min(end + 0.30, start + 0.95),
            "intensity": intensity,
            "is_shout": is_shout,
        })

    return events


def _ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - pow(1 - t, 3)


def _ease_in_out_sine(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return -(math.cos(math.pi * t) - 1) / 2


def _apply_cinematic_camera_motion(clip, words: List[Dict], debug: bool = False):
    events = _collect_zoom_events(words)
    base_zoom = 1.03

    duration = max(0.01, float(getattr(clip, "duration", 0.0) or 0.0))
    state = {"x": 0.0, "y": 0.0, "z": base_zoom, "last_t": 0.0}

    def desired_zoom(t: float) -> float:
        z = base_zoom
        for event in events:
            if t < event["start"] - 0.12 or t > event["end"] + 0.18:
                continue
            peak_t = max(event["start"], min(event["peak"], t))
            rise = _ease_out_cubic(max(0.0, min(1.0, (peak_t - event["start"]) / max(1e-6, event["peak"] - event["start"])) ))
            decay = 1.0 if t <= event["peak"] else (1.0 - _ease_in_out_sine((t - event["peak"]) / max(1e-6, event["end"] - event["peak"])))
            env = min(rise, decay)
            z += (0.03 + 0.06 * event["intensity"]) * env
        return max(1.0, min(1.18, z))

    def smooth_step(target: float, current: float, dt: float, speed: float) -> float:
        a = max(0.0, min(1.0, dt * speed))
        return current + (target - current) * a

    def position_at(t: float):
        dt = max(0.0, min(0.2, t - state["last_t"]))
        state["last_t"] = t
        target_x = math.sin(t * 0.18) * 2.2
        target_y = math.cos(t * 0.14) * 1.6
        if abs(target_x - state["x"]) < 1.2:
            target_x = state["x"]
        if abs(target_y - state["y"]) < 1.2:
            target_y = state["y"]
        state["x"] = smooth_step(target_x, state["x"], dt, 2.1)
        state["y"] = smooth_step(target_y, state["y"], dt, 2.1)
        state["z"] = smooth_step(desired_zoom(t), state["z"], dt, 2.6)
        return (state["x"], state["y"])

    result = clip.resize(lambda t: state.setdefault("z", base_zoom) if t <= 0 else desired_zoom(float(t))).set_position(position_at)
    return result


def _collect_words(segments: List[Dict]) -> List[Dict]:
    words: List[Dict] = []
    for segment in segments:
        segment_words = segment.get("words", [])
        if segment_words:
            words.extend(segment_words)
    return words


def _probe_streams(label: str, media_path: str) -> str:
    ffprobe_cmd = [
        "ffprobe",
        "-hide_banner",
        "-show_streams",
        media_path,
    ]
    probe_proc = subprocess.run(ffprobe_cmd, capture_output=True, text=True, check=False)
    combined_output = (probe_proc.stdout or "") + (probe_proc.stderr or "")
    video_streams = combined_output.count("codec_type=video") + combined_output.count("Video:")
    audio_streams = combined_output.count("codec_type=audio") + combined_output.count("Audio:")
    print(f"[PIPELINE][ffprobe][{label}] path={media_path}")
    print(f"[PIPELINE][ffprobe][{label}] returncode={probe_proc.returncode}")
    print(f"[PIPELINE][ffprobe][{label}] video_streams_detected={video_streams}")
    print(f"[PIPELINE][ffprobe][{label}] audio_streams_detected={audio_streams}")
    print(f"[PIPELINE][ffprobe][{label}] output:\n{combined_output}")
    return combined_output


def _probe_dimensions(media_path: str) -> tuple[int, int]:
    probe_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=p=0:s=x",
        media_path,
    ]
    proc = subprocess.run(probe_cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Failed to probe video dimensions for {media_path}: {proc.stderr}")
    data = (proc.stdout or "").strip()
    if "x" not in data:
        raise RuntimeError(f"Could not parse dimensions for {media_path}: {data}")
    w, h = data.split("x", 1)
    return int(w), int(h)


def _create_proxy_if_needed(video_path: str) -> tuple[str, bool]:
    width, _ = _probe_dimensions(video_path)
    if width <= MAX_TRACKING_WIDTH:
        return video_path, False

    proxy_file = tempfile.NamedTemporaryFile(prefix="proxy_1080_", suffix=".mp4", delete=False)
    proxy_file.close()
    proxy_path = proxy_file.name
    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vf", "scale=1920:-2",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-an",
        proxy_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Failed to create proxy video.\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    return proxy_path, True


def create_tiktok_subtitles(video_path, segments, output_path, speaker_segments=None):
    """Render premium subtitles and export video.

    API intentionally unchanged.
    """
    tracking_source, proxy_created = _create_proxy_if_needed(video_path)
    base_clip = VideoFileClip(tracking_source)

    print(f"[REFRAME] proxy_created={proxy_created}")
    print(f"[REFRAME] tracking_resolution={int(base_clip.w)}x{int(base_clip.h)}")
    print(f"[REFRAME] render_resolution={TARGET_RENDER_SIZE[0]}x{TARGET_RENDER_SIZE[1]}")
    print(f"[REFRAME] memory_safe_mode={SAFE_CPU_RENDER}")

    sample_fps = 4.0 if SAFE_CPU_RENDER else 6.0
    max_zoom = 1.08 if SAFE_CPU_RENDER else 1.12
    reframer = ReframingService(sample_fps=sample_fps, max_zoom=max_zoom)
    caption_position = "bottom"
    preset = "cinematic"
    debug_layout = False
    reframed_video = reframer.apply(base_clip, speaker_segments=speaker_segments, debug=debug_layout)

    words = _collect_words(segments)
    if segments and isinstance(segments[0], dict):
        segments[0]["camera_keyframes"] = reframer.camera_keyframes
    renderer = SubtitleRenderer()
    cinematic_video = reframed_video if SAFE_CPU_RENDER else _apply_cinematic_camera_motion(reframed_video, words, debug=debug_layout)
    word_layers = renderer.build_word_layers(
        words=words,
        video_w=int(cinematic_video.w),
        video_h=int(cinematic_video.h),
        caption_position=caption_position,
        preset=preset,
        debug_layout=debug_layout,
    )

    final_video = CompositeVideoClip([cinematic_video, *word_layers], size=cinematic_video.size)
    silent_output = output_path.replace(".mp4", "_silent.mp4")
    audio_output = output_path.replace(".mp4", ".aac")
    mux_output = output_path.replace(".mp4", "_mux.mp4")

    print(f"[PIPELINE] original_file={video_path}")
    _probe_streams("original", video_path)

    render_fps = 20 if SAFE_CPU_RENDER else 24
    final_video.write_videofile(
        silent_output,
        codec="libx264",
        audio=False,
        fps=render_fps,
        preset="veryfast",
        threads=4,
        ffmpeg_params=["-pix_fmt", "yuv420p"],
    )

    final_video.close()
    cinematic_video.close()
    reframed_video.close()
    base_clip.close()

    print(f"[PIPELINE] raw_clip={video_path}")
    _probe_streams("raw_clip", video_path)
    print(f"[PIPELINE] silent_output={silent_output}")
    _probe_streams("silent_output", silent_output)

    extract_audio_cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "copy",
        audio_output,
    ]
    extract_audio_proc = subprocess.run(extract_audio_cmd, capture_output=True, text=True, check=False)
    print(f"[PIPELINE][extract_audio] cmd={' '.join(extract_audio_cmd)}")
    print(f"[PIPELINE][extract_audio] returncode={extract_audio_proc.returncode}")
    print(f"[PIPELINE][extract_audio] stderr:\n{extract_audio_proc.stderr}")
    if extract_audio_proc.returncode != 0:
        raise RuntimeError(
            f"Failed to extract source audio with ffmpeg.\n"
            f"STDOUT:\n{extract_audio_proc.stdout}\nSTDERR:\n{extract_audio_proc.stderr}"
        )

    print(f"[PIPELINE] audio_extract={audio_output} exists={os.path.exists(audio_output)}")
    if os.path.exists(audio_output):
        _probe_streams("audio_extract", audio_output)

    mux_cmd = [
        "ffmpeg",
        "-y",
        "-i", silent_output,
        "-i", audio_output,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        mux_output,
    ]
    mux_proc = subprocess.run(mux_cmd, capture_output=True, text=True, check=False)
    print(f"[PIPELINE][mux] cmd={' '.join(mux_cmd)}")
    print(f"[PIPELINE][mux] returncode={mux_proc.returncode}")
    print(f"[PIPELINE][mux] stderr:\n{mux_proc.stderr}")
    if mux_proc.returncode != 0:
        raise RuntimeError(
            f"Failed to mux final video/audio with ffmpeg.\n"
            f"STDOUT:\n{mux_proc.stdout}\nSTDERR:\n{mux_proc.stderr}"
        )

    print(f"[PIPELINE] mux_output={mux_output} exists={os.path.exists(mux_output)}")
    if os.path.exists(mux_output):
        _probe_streams("mux_output", mux_output)

    os.replace(mux_output, output_path)

    ffprobe_cmd = ["ffprobe", output_path]
    ffprobe_proc = subprocess.run(ffprobe_cmd, capture_output=True, text=True, check=False)
    ffprobe_output = (ffprobe_proc.stdout or "") + (ffprobe_proc.stderr or "")
    print(f"[ffprobe] {output_path}\n{ffprobe_output}")
    if "Audio: aac" not in ffprobe_output:
        raise RuntimeError(f"Rendered video is missing AAC audio stream: {output_path}")
    if "Video:" not in ffprobe_output:
        raise RuntimeError(f"Rendered video is missing video stream: {output_path}")

    final_w, final_h = _probe_dimensions(output_path)
    if (final_w, final_h) != TARGET_RENDER_SIZE:
        raise RuntimeError(f"Rendered video has invalid size {final_w}x{final_h}; expected 1080x1920")

    if proxy_created and tracking_source != video_path and os.path.exists(tracking_source):
        os.remove(tracking_source)

    return output_path
