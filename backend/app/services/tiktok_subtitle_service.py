import os
from typing import Dict, List, Optional, Sequence

os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"

from moviepy.editor import CompositeVideoClip, TextClip, VideoFileClip


# ---------- Visual tuning (TikTok/Reels premium style) ----------
BASE_FONT_CANDIDATES: Sequence[str] = (
    "Montserrat-ExtraBold",
    "Montserrat-Bold",
    "Arial-Bold",
)
ACTIVE_COLOR = "#FFD400"
INACTIVE_COLOR = "white"
STROKE_COLOR = "black"

# timing/animation
POP_IN_SECONDS = 0.10
ACTIVE_SCALE_BOOST = 0.10

# layout
MAX_WORDS_PER_LINE = 3
WIDTH_RATIO = 0.86
BOTTOM_SAFE_MARGIN_RATIO = 0.10


def _clean_word(raw_word: str) -> str:
    return (raw_word or "").strip()


def _resolve_font() -> Optional[str]:
    """Return first available font candidate name.

    MoviePy/ImageMagick behavior varies by environment; falling back to None
    keeps compatibility with existing pipeline.
    """
    for candidate in BASE_FONT_CANDIDATES:
        try:
            TextClip(
                "TEST",
                fontsize=40,
                font=candidate,
                color="white",
                method="caption",
                size=(300, None),
            ).close()
            return candidate
        except Exception:
            continue
    return None


def _smart_group_words(words: List[Dict]) -> List[List[Dict]]:
    """Group words into caption lines with up to MAX_WORDS_PER_LINE words.

    Keeps timing from WhisperX words and prefers breaking at punctuation when possible.
    """
    grouped: List[List[Dict]] = []
    current: List[Dict] = []

    for word in words:
        if "start" not in word or "end" not in word:
            continue

        token = _clean_word(word.get("word", ""))
        if not token:
            continue

        current.append({**word, "word": token})
        end_with_break = token.endswith((".", "!", "?", ",", ";", ":"))

        if len(current) >= MAX_WORDS_PER_LINE or end_with_break:
            grouped.append(current)
            current = []

    if current:
        grouped.append(current)

    return grouped


def _pop_in_resize(t: float, clip_duration: float) -> float:
    if t <= 0:
        return 1.0
    pop_progress = min(t / max(POP_IN_SECONDS, 0.001), 1.0)
    # Smooth ease-out
    eased = 1 - (1 - pop_progress) ** 2
    return 1.0 + (ACTIVE_SCALE_BOOST * (1.0 - (1.0 - eased)))


def _create_word_clip(
    text: str,
    start: float,
    end: float,
    line_width: int,
    y_pos: int,
    font_name: Optional[str],
    is_active: bool,
) -> TextClip:
    color = ACTIVE_COLOR if is_active else INACTIVE_COLOR
    fontsize = 108 if is_active else 98

    clip = TextClip(
        text.upper(),
        fontsize=fontsize,
        font=font_name,
        color=color,
        stroke_color=STROKE_COLOR,
        stroke_width=8 if is_active else 7,
        kerning=-1,
        method="caption",
        size=(line_width, None),
        align="center",
    ).set_start(start).set_end(end).set_position(("center", y_pos))

    if is_active:
        clip = clip.resize(lambda t: _pop_in_resize(t, end - start))

    return clip


def _create_glow_clip(
    text: str,
    start: float,
    end: float,
    line_width: int,
    y_pos: int,
    font_name: Optional[str],
) -> TextClip:
    # Lightweight glow using a soft, wider, semi-transparent layer.
    return (
        TextClip(
            text.upper(),
            fontsize=112,
            font=font_name,
            color=ACTIVE_COLOR,
            stroke_color=STROKE_COLOR,
            stroke_width=11,
            kerning=-1,
            method="caption",
            size=(line_width, None),
            align="center",
        )
        .set_opacity(0.16)
        .set_start(start)
        .set_end(end)
        .set_position(("center", y_pos + 1))
    )


def _build_caption_layers(
    segment_words: List[Dict],
    font_name: Optional[str],
    line_width: int,
    y_pos: int,
) -> List[TextClip]:
    clips: List[TextClip] = []
    lines = _smart_group_words(segment_words)

    for line_words in lines:
        line_start = line_words[0]["start"]
        line_end = line_words[-1]["end"]

        # Inactive base line (all words white)
        base_text = " ".join(w["word"] for w in line_words)
        base_line = _create_word_clip(
            text=base_text,
            start=line_start,
            end=line_end,
            line_width=line_width,
            y_pos=y_pos,
            font_name=font_name,
            is_active=False,
        )
        clips.append(base_line)

        # Active highlighted word overlays with exact WhisperX word timing.
        for active_index, word_data in enumerate(line_words):
            word_start = word_data["start"]
            word_end = word_data["end"]

            rendered_words = []
            for idx, wd in enumerate(line_words):
                token = wd["word"]
                if idx == active_index:
                    rendered_words.append(token)
                else:
                    # keep spacing/alignment while hiding non-active overlays
                    rendered_words.append(" ")

            active_text = " ".join(rendered_words)
            glow = _create_glow_clip(
                text=active_text,
                start=word_start,
                end=word_end,
                line_width=line_width,
                y_pos=y_pos,
                font_name=font_name,
            )
            active = _create_word_clip(
                text=active_text,
                start=word_start,
                end=word_end,
                line_width=line_width,
                y_pos=y_pos,
                font_name=font_name,
                is_active=True,
            )
            clips.extend([glow, active])

    return clips


def create_tiktok_subtitles(video_path, segments, output_path):
    """Generate premium TikTok/Reels-style subtitles using WhisperX word timing."""
    video = VideoFileClip(video_path)
    font_name = _resolve_font()

    line_width = int(video.w * WIDTH_RATIO)
    y_pos = int(video.h * (1.0 - BOTTOM_SAFE_MARGIN_RATIO)) - 180
    y_pos = max(int(video.h * 0.68), min(y_pos, int(video.h * 0.86)))

    text_clips: List[TextClip] = []

    for segment in segments:
        words = segment.get("words", [])
        if not words:
            continue

        text_clips.extend(
            _build_caption_layers(
                segment_words=words,
                font_name=font_name,
                line_width=line_width,
                y_pos=y_pos,
            )
        )

    final = CompositeVideoClip([video, *text_clips])

    final.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=30)

    video.close()
    final.close()
    return output_path
