from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Sequence, Tuple

from moviepy.editor import TextClip


@dataclass(frozen=True)
class SubtitleStyleConfig:
    font_candidates: Sequence[str] = ("Montserrat-ExtraBold", "Montserrat-Bold", "Arial-Bold")
    emphasis_keywords: frozenset[str] = frozenset({
        "atencao", "atenção", "urgente", "segredo", "dinheiro", "nunca",
        "impossivel", "impossível", "choque", "milionario", "milionário",
        "viral", "proibido", "explosao", "explosão",
    })
    normal_font_size: int = 108
    emphasis_font_size: int = 118
    normal_stroke_width: int = 7
    emphasis_stroke_width: int = 9
    normal_fill_color: str = "#FFEB3B"
    emphasis_fill_color: str = "#FF7A00"
    normal_glow_color: str = "#FFD166"
    emphasis_glow_color: str = "#FF4500"
    safe_bottom_ratio: float = 0.165
    min_safe_bottom_px: int = 180


class SubtitleRenderer:
    def __init__(self, config: SubtitleStyleConfig | None = None):
        self.config = config or SubtitleStyleConfig()
        self._style_cache: Dict[str, Dict[str, float | int | str]] = {}

    @staticmethod
    def _normalize_word(word: str) -> str:
        return re.sub(r"[^\wÀ-ÿ]", "", (word or "").strip().lower())

    def _is_emphasis_word(self, word: str) -> bool:
        return self._normalize_word(word) in self.config.emphasis_keywords

    def resolve_font(self) -> Optional[str]:
        for candidate in self.config.font_candidates:
            try:
                TextClip("TEST", fontsize=40, font=candidate, color="white", method="caption", size=(300, None)).close()
                return candidate
            except Exception:
                continue
        return "Arial-Bold"

    def safe_caption_y(self, video_h: int, position: Literal["top", "middle", "bottom"] = "bottom") -> int:
        top_safe = int(video_h * 0.14)
        middle_safe = int(video_h * 0.50)
        bottom_safe = video_h - max(int(video_h * self.config.safe_bottom_ratio), self.config.min_safe_bottom_px)
        return {"top": top_safe, "middle": middle_safe, "bottom": bottom_safe}.get(position, bottom_safe)

    @staticmethod
    def _ease_out_cubic(t: float) -> float:
        return 1 - pow(1 - max(0.0, min(1.0, t)), 3)

    def _soft_bounce(self, local_t: float) -> float:
        if local_t <= 0:
            return 0.0
        if local_t < 0.18:
            return self._ease_out_cubic(local_t / 0.18)
        if local_t < 0.38:
            n = (local_t - 0.18) / 0.20
            return 1.0 + math.sin(n * math.pi) * 0.12
        return 1.0

    def _build_word_position(self, base_y: int, word_start: float, amplitude: float, float_freq: float):
        def dynamic_position(t: float) -> Tuple[str, float]:
            local_t = max(0.0, t - word_start)
            float_offset = math.sin((t + word_start) * float_freq * 2 * math.pi) * amplitude
            bounce_offset = -8.5 * self._soft_bounce(local_t)
            return ("center", base_y + float_offset + bounce_offset)

        return dynamic_position

    def _build_scale_fn(self, base_size: int, emphasis: bool):
        peak = 1.20 if emphasis else 1.10

        def scale_fn(t: float) -> float:
            s = self._soft_bounce(t)
            return 1.0 + (peak - 1.0) * s

        return scale_fn

    def _resolve_style(self, preset: str, video_h: int) -> Dict[str, float | int | str]:
        key = f"{preset}:{video_h}"
        if key in self._style_cache:
            return self._style_cache[key]
        base_size = int(max(56, min(132, video_h * 0.095)))
        styles = {
            "cinematic": {"font_size": base_size, "line_kerning": -2, "shadow_opacity": 0.46, "glow_opacity": 0.30},
            "tiktok": {"font_size": int(base_size * 0.9), "line_kerning": -1, "shadow_opacity": 0.38, "glow_opacity": 0.24},
            "hormozi": {"font_size": int(base_size * 1.02), "line_kerning": -2, "shadow_opacity": 0.52, "glow_opacity": 0.28},
            "minimal": {"font_size": int(base_size * 0.82), "line_kerning": 0, "shadow_opacity": 0.30, "glow_opacity": 0.16},
            "neon": {"font_size": int(base_size * 0.96), "line_kerning": -1, "shadow_opacity": 0.43, "glow_opacity": 0.36},
        }
        self._style_cache[key] = styles.get(preset, styles["cinematic"])
        return self._style_cache[key]

    def build_word_layers(self, words: List[Dict], video_w: int, video_h: int, caption_position: Literal["top", "middle", "bottom"] = "bottom", preset: str = "cinematic") -> List[TextClip]:
        clips: List[TextClip] = []
        max_caption_w = int(video_w * 0.84)
        base_y = self.safe_caption_y(video_h, caption_position)
        style = self._resolve_style(preset, video_h)
        font_name = self.resolve_font()

        for word_data in words:
            if "start" not in word_data or "end" not in word_data:
                continue
            raw_word = word_data.get("word", "")
            word = (raw_word or "").upper().strip()
            if not word:
                continue
            word_start = float(word_data["start"])
            word_end = float(word_data["end"])
            if word_end <= word_start:
                continue

            duration = max(0.01, word_end - word_start)
            emphasis = self._is_emphasis_word(raw_word)
            font_size = int(style["font_size"]) + (14 if emphasis else 0)
            stroke_width = self.config.emphasis_stroke_width if emphasis else self.config.normal_stroke_width
            fill_color = self.config.emphasis_fill_color if emphasis else self.config.normal_fill_color
            glow_color = self.config.emphasis_glow_color if emphasis else self.config.normal_glow_color

            pos_fn = self._build_word_position(base_y, word_start, 8.0 if emphasis else 5.0, 1.6 if emphasis else 1.25)
            fade_in_t = min(0.12, duration * 0.45)
            fade_out_t = min(0.10, duration * 0.38)
            pop_scale = self._build_scale_fn(font_size, emphasis)

            shadow = (
                TextClip(word, fontsize=font_size, font=font_name, color="#000000", kerning=int(style["line_kerning"]), method="caption", size=(max_caption_w, None), align="center", stroke_color="#111111", stroke_width=stroke_width + 3)
                .set_opacity(float(style["shadow_opacity"]) + (0.08 if emphasis else 0.0))
                .set_position(lambda t, p=pos_fn: ("center", p(t)[1] + 8))
                .set_start(word_start).set_end(word_end).crossfadein(fade_in_t).crossfadeout(fade_out_t)
            )
            glow = (
                TextClip(word, fontsize=font_size, font=font_name, color=glow_color if preset != "neon" else "#71A6FF", kerning=int(style["line_kerning"]), method="caption", size=(max_caption_w, None), align="center", stroke_color=glow_color, stroke_width=stroke_width + 2)
                .set_opacity(float(style["glow_opacity"]) + (0.08 if emphasis else 0.0))
                .set_position(pos_fn)
                .set_start(word_start).set_end(word_end).crossfadein(fade_in_t).crossfadeout(fade_out_t)
            )

            def text_layer_position(t, p=pos_fn, emph=emphasis, ws=word_start):
                x, y = p(t)
                return (x, y + math.sin((t + ws) * 48.0) * 1.5) if emph else (x, y)

            text = (
                TextClip(word, fontsize=font_size, font=font_name, color="#FFD400" if emphasis else "#FFFFFF", stroke_color="#000000", stroke_width=stroke_width, kerning=int(style["line_kerning"]), method="caption", size=(max_caption_w, None), align="center")
                .resize(lambda t, sf=pop_scale: sf(t))
                .set_position(text_layer_position)
                .set_start(word_start).set_end(word_end).crossfadein(fade_in_t).crossfadeout(fade_out_t)
            )
            clips.extend([shadow, glow, text])
        return clips
