from __future__ import annotations

import os
import math
import re
import subprocess
from typing import Dict, List

from moviepy.editor import CompositeVideoClip, VideoFileClip

from app.services.reframing_service import ReframingService
from app.services.subtitle_renderer import SubtitleRenderer

os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"


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


def _apply_cinematic_camera_motion(clip, words: List[Dict]):
    events = _collect_zoom_events(words)
    if not events:
        return clip

    base_zoom = 1.025

    def envelope(event, t: float) -> float:
        if t < event["start"] or t > event["end"]:
            return 0.0
        if t <= event["peak"]:
            p = (t - event["start"]) / max(1e-6, event["peak"] - event["start"])
            return _ease_out_cubic(p)
        p = (t - event["peak"]) / max(1e-6, event["end"] - event["peak"])
        return 1.0 - _ease_in_out_sine(p)

    def zoom_at(t: float) -> float:
        dynamic = 0.0
        for event in events:
            env = envelope(event, t)
            if env <= 0:
                continue
            dynamic += (0.08 + 0.14 * event["intensity"]) * env
        return min(1.34, base_zoom + dynamic)

    def position_at(t: float):
        shake_x = 0.0
        shake_y = 0.0
        for i, event in enumerate(events):
            env = envelope(event, t)
            if env <= 0:
                continue
            micro_amp = (1.6 + 4.6 * event["intensity"]) * env
            if event["is_shout"]:
                micro_amp *= 1.18
            shake_x += math.sin((t * 13.0) + (i * 1.7)) * micro_amp
            shake_y += math.cos((t * 11.0) + (i * 1.2)) * (micro_amp * 0.6)

        natural_drift = math.sin(t * 0.55) * 3.0
        return (shake_x, shake_y + natural_drift)

    return clip.resize(lambda t: zoom_at(float(t))).set_position(position_at)


def _collect_words(segments: List[Dict]) -> List[Dict]:
    words: List[Dict] = []
    for segment in segments:
        segment_words = segment.get("words", [])
        if segment_words:
            words.extend(segment_words)
    return words


def create_tiktok_subtitles(video_path, segments, output_path):
    """Render premium subtitles and export video.

    API intentionally unchanged.
    """
    base_clip = VideoFileClip(video_path)

    reframer = ReframingService()
    reframed_video = reframer.apply(base_clip)

    words = _collect_words(segments)
    cinematic_video = _apply_cinematic_camera_motion(reframed_video, words)
    if base_clip.audio:
        cinematic_video = cinematic_video.set_audio(base_clip.audio)

    renderer = SubtitleRenderer()
    word_layers = renderer.build_word_layers(
        words=words,
        video_w=int(cinematic_video.w),
        video_h=int(cinematic_video.h),
    )

    final_video = CompositeVideoClip([cinematic_video, *word_layers], size=cinematic_video.size)
    final_video.audio = base_clip.audio
    if base_clip.audio:
        final_video = final_video.set_audio(base_clip.audio)

    final_video.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile="temp-audio.m4a",
        remove_temp=True,
        fps=24,
        preset="medium",
    )

    ffprobe_cmd = [
        "ffprobe",
        "-v", "error",
        "-show_streams",
        "-i", output_path,
    ]
    ffprobe_proc = subprocess.run(ffprobe_cmd, capture_output=True, text=True, check=False)
    ffprobe_output = (ffprobe_proc.stdout or "") + (ffprobe_proc.stderr or "")
    print(f"[ffprobe] {output_path}\n{ffprobe_output}")
    if "codec_type=audio" not in ffprobe_output or "codec_name=aac" not in ffprobe_output:
        raise RuntimeError(f"Rendered video is missing AAC audio stream: {output_path}")

    final_video.close()
    cinematic_video.close()
    reframed_video.close()
    if reframed_video is not base_clip:
        base_clip.close()

    return output_path
