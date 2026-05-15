import math
import os
import re

os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"

from moviepy.editor import CompositeVideoClip, TextClip, VideoFileClip

from app.services.reframing_service import ReframingService


# Keywords that should receive stronger emphasis and motion.
EMPHASIS_KEYWORDS = {
    "atencao",
    "atenção",
    "urgente",
    "segredo",
    "dinheiro",
    "nunca",
    "impossivel",
    "impossível",
    "choque",
    "milionario",
    "milionário",
    "viral",
    "proibido",
    "explosao",
    "explosão",
}


def _normalize_word(word):
    return re.sub(r"[^\wÀ-ÿ]", "", (word or "").strip().lower())


def _is_emphasis_word(word):
    return _normalize_word(word) in EMPHASIS_KEYWORDS


def _ease_out_cubic(t):
    return 1 - pow(1 - max(0.0, min(1.0, t)), 3)


def _soft_bounce(local_t):
    # Subtle and premium-looking bounce (quick rise + smooth settle)
    if local_t <= 0:
        return 0.0
    if local_t < 0.18:
        n = local_t / 0.18
        return _ease_out_cubic(n) * 1.0
    if local_t < 0.38:
        n = (local_t - 0.18) / 0.20
        return 1.0 + math.sin(n * math.pi) * 0.12
    return 1.0


def _safe_caption_y(video_h):
    # Keeps text away from TikTok UI + responsive to different formats.
    bottom_margin = max(int(video_h * 0.165), 180)
    return max(0, video_h - bottom_margin)


def _build_word_position(base_y, word_start, amplitude=6.0, float_freq=1.35):
    def dynamic_position(t):
        local_t = max(0.0, t - word_start)
        # Micro cinematic float + subtle settling bounce.
        float_offset = math.sin((t + word_start) * float_freq * 2 * math.pi) * amplitude
        bounce_offset = -8.5 * _soft_bounce(local_t)
        return ("center", base_y + float_offset + bounce_offset)

    return dynamic_position


def _build_word_scale(base_size, emphasis):
    # Stronger pop for keywords, still smooth.
    peak = 1.20 if emphasis else 1.10

    def scale_fn(t):
        s = _soft_bounce(t)
        return int(base_size * (1.0 + (peak - 1.0) * s))

    return scale_fn


def create_tiktok_subtitles(video_path, segments, output_path):
    """
    Cinematic subtitle renderer tuned for viral-style short-form content.

    API intentionally kept unchanged for backward compatibility.
    """
    video = VideoFileClip(video_path)

    # Auto cinematic reframing for horizontal footage (OpusClip/CapCut style).
    reframer = ReframingService()
    video = reframer.apply(video)

    video_w = int(video.w)
    video_h = int(video.h)

    max_caption_w = int(video_w * 0.84)
    base_y = _safe_caption_y(video_h)

    text_clips = []

    for segment in segments:
        words = segment.get("words", [])
        if not words:
            continue

        for word_data in words:
            if "start" not in word_data or "end" not in word_data:
                continue

            raw_word = word_data.get("word", "")
            word = raw_word.upper().strip()
            if not word:
                continue

            word_start = float(word_data["start"])
            word_end = float(word_data["end"])
            if word_end <= word_start:
                continue

            duration = max(0.01, word_end - word_start)
            emphasis = _is_emphasis_word(raw_word)

            font_size = 118 if emphasis else 108
            stroke_width = 9 if emphasis else 7
            fill_color = "#FFEB3B" if not emphasis else "#FF7A00"
            glow_color = "#FFD166" if not emphasis else "#FF4500"

            pos_fn = _build_word_position(
                base_y=base_y,
                word_start=word_start,
                amplitude=8.0 if emphasis else 5.0,
                float_freq=1.6 if emphasis else 1.25,
            )

            fade_in_t = min(0.12, duration * 0.45)
            fade_out_t = min(0.10, duration * 0.38)

            # Soft shadow for real depth/contrast.
            shadow = (
                TextClip(
                    word,
                    fontsize=font_size,
                    font="Arial-Bold",
                    color="#000000",
                    kerning=-2,
                    method="caption",
                    size=(max_caption_w, None),
                    align="center",
                    stroke_color="#111111",
                    stroke_width=stroke_width + 3,
                )
                .set_opacity(0.42 if not emphasis else 0.55)
                .set_position(lambda t, p=pos_fn: ("center", p(t)[1] + 8))
                .set_start(word_start)
                .set_end(word_end)
                .crossfadein(fade_in_t)
                .crossfadeout(fade_out_t)
            )

            # Natural glow layer.
            glow = (
                TextClip(
                    word,
                    fontsize=font_size,
                    font="Arial-Bold",
                    color=glow_color,
                    kerning=-2,
                    method="caption",
                    size=(max_caption_w, None),
                    align="center",
                    stroke_color=glow_color,
                    stroke_width=stroke_width + 2,
                )
                .set_opacity(0.20 if not emphasis else 0.34)
                .set_position(pos_fn)
                .set_start(word_start)
                .set_end(word_end)
                .crossfadein(fade_in_t)
                .crossfadeout(fade_out_t)
            )

            # Main text with smooth pop-in scale and optional micro-shake for emphasis.
            pop_scale = _build_word_scale(font_size, emphasis)

            def text_layer_position(t, p=pos_fn, emph=emphasis):
                x, y = p(t)
                if emph:
                    shake = math.sin((t + word_start) * 48.0) * 1.5
                    return (x, y + shake)
                return (x, y)

            txt_clip = (
                TextClip(
                    word,
                    fontsize=font_size,
                    font="Arial-Bold",
                    color=fill_color,
                    stroke_color="#0D0D0D",
                    stroke_width=stroke_width,
                    kerning=-2,
                    method="caption",
                    size=(max_caption_w, None),
                    align="center",
                )
                .resize(lambda t, ps=pop_scale: ps(t) / float(font_size))
                .set_position(text_layer_position)
                .set_start(word_start)
                .set_end(word_end)
                .crossfadein(fade_in_t)
                .crossfadeout(fade_out_t)
            )

            text_clips.extend([shadow, glow, txt_clip])

    final = CompositeVideoClip([video, *text_clips], size=video.size)

    final.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        fps=30,
        threads=max(2, min(8, (os.cpu_count() or 4))),
        preset="medium",
    )

    return output_path
