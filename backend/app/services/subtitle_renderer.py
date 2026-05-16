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
    safe_top_ratio: float = 0.10
    safe_side_ratio: float = 0.08
    safe_bottom_ratio: float = 0.14
    min_safe_side_px: int = 48
    min_safe_top_px: int = 44
    min_safe_bottom_px: int = 112
    max_caption_width_ratio: float = 0.70
    max_words_per_line: int = 3
    max_lines_per_caption: int = 2
    cinematic_line_height_ratio: float = 1.22


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

    def _safe_area(self, video_w: int, video_h: int) -> Dict[str, int]:
        side = max(int(video_w * self.config.safe_side_ratio), self.config.min_safe_side_px)
        top = max(int(video_h * self.config.safe_top_ratio), self.config.min_safe_top_px)
        bottom = max(int(video_h * self.config.safe_bottom_ratio), self.config.min_safe_bottom_px)
        return {"left": side, "right": video_w - side, "top": top, "bottom": video_h - bottom}

    def _dynamic_font_size(self, video_w: int, video_h: int, words_count: int, caption_position: Literal["top", "middle", "bottom"], preset_factor: float) -> int:
        base = min(video_w * 0.063, video_h * 0.105)
        words_penalty = 1.0 - min(0.22, max(0, words_count - 1) * 0.035)
        position_factor = {"top": 0.94, "middle": 1.0, "bottom": 0.96}.get(caption_position, 1.0)
        size = int(base * words_penalty * position_factor * preset_factor)
        return max(34, min(104, size))

    def _build_caption_lines(self, words: List[str]) -> List[List[str]]:
        cleaned = [w for w in words if w and w.strip()]
        if not cleaned:
            return []
        if len(cleaned) <= self.config.max_words_per_line:
            return [cleaned]

        split_ix = min(self.config.max_words_per_line, max(1, len(cleaned) // 2))
        punctuated = {",", ".", ";", ":", "?", "!"}
        for i in range(1, min(len(cleaned), self.config.max_words_per_line + 1)):
            if any(cleaned[i - 1].endswith(p) for p in punctuated):
                split_ix = i

        first = cleaned[:split_ix]
        second = cleaned[split_ix: split_ix + self.config.max_words_per_line]
        if not second:
            return [first]
        return [first, second][:self.config.max_lines_per_caption]

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
            return 1.0 + math.sin(n * math.pi) * 0.10
        return 1.0

    def _resolve_style(self, preset: str) -> Dict[str, float | int | str]:
        if preset in self._style_cache:
            return self._style_cache[preset]
        styles = {
            "cinematic": {"line_kerning": -1, "shadow_opacity": 0.32, "glow_opacity": 0.18, "preset_factor": 1.0},
            "tiktok": {"line_kerning": 0, "shadow_opacity": 0.28, "glow_opacity": 0.14, "preset_factor": 0.92},
            "hormozi": {"line_kerning": -1, "shadow_opacity": 0.34, "glow_opacity": 0.18, "preset_factor": 0.98},
            "minimal": {"line_kerning": 0, "shadow_opacity": 0.24, "glow_opacity": 0.10, "preset_factor": 0.88},
            "neon": {"line_kerning": 0, "shadow_opacity": 0.30, "glow_opacity": 0.22, "preset_factor": 0.94},
        }
        self._style_cache[preset] = styles.get(preset, styles["cinematic"])
        return self._style_cache[preset]

    def _caption_center_y(self, safe: Dict[str, int], video_h: int, caption_position: Literal["top", "middle", "bottom"]) -> int:
        if caption_position == "top":
            return safe["top"] + int(video_h * 0.14)
        if caption_position == "middle":
            return int(video_h * 0.53)
        return safe["bottom"] - int(video_h * 0.08)

    def build_word_layers(self, words: List[Dict], video_w: int, video_h: int, caption_position: Literal["top", "middle", "bottom"] = "bottom", preset: str = "cinematic", debug_layout: bool = False) -> List[TextClip]:
        clips: List[TextClip] = []
        if not words:
            return clips

        safe = self._safe_area(video_w, video_h)
        max_caption_w = int(video_w * self.config.max_caption_width_ratio)
        style = self._resolve_style(preset)
        font_name = self.resolve_font()
        caption_center_y = self._caption_center_y(safe, video_h, caption_position)

        phrase_words = [str(w.get("word", "")).upper().strip() for w in words[:6]]
        phrase_words = [w for w in phrase_words if w]
        lines = self._build_caption_lines(phrase_words)
        if not lines:
            return clips

        line_texts = [" ".join(line) for line in lines]
        base_size = self._dynamic_font_size(video_w, video_h, len(phrase_words), caption_position, float(style["preset_factor"]))
        line_height_px = int(base_size * self.config.cinematic_line_height_ratio)
        block_shift = int((len(line_texts) - 1) * line_height_px * 0.5)

        for word_data in words:
            if "start" not in word_data or "end" not in word_data:
                continue
            raw_word = str(word_data.get("word", "")).strip()
            if not raw_word:
                continue
            word = raw_word.upper()
            word_start = float(word_data["start"])
            word_end = float(word_data["end"])
            if word_end <= word_start:
                continue

            emphasis = self._is_emphasis_word(raw_word)
            font_size = int(base_size * (1.12 if emphasis else 1.0))
            stroke_width = max(2, int(font_size * 0.055))
            fill_color = "#FFD24A" if emphasis else "#FFFFFF"
            glow_color = "#FFB347" if emphasis else "#B6E3FF"

            duration = max(0.01, word_end - word_start)
            fade_in_t = min(0.08, duration * 0.35)
            fade_out_t = min(0.08, duration * 0.30)

            for line_idx, line_text in enumerate(line_texts):
                y = caption_center_y - block_shift + (line_idx * line_height_px)
                contains_active = word in line_text.split()

                inactive = (
                    TextClip(line_text, fontsize=base_size, font=font_name, color="#FFFFFF", kerning=int(style["line_kerning"]), method="caption", size=(max_caption_w, None), align="center", stroke_color="#000000", stroke_width=stroke_width)
                    .set_opacity(0.94)
                    .set_position(("center", y))
                    .set_start(word_start)
                    .set_end(word_end)
                )
                clips.append(inactive)

                if not contains_active:
                    continue

                scale_peak = 1.12 if emphasis else 1.08

                def scale_fn(t: float, st=word_start, en=word_end, peak=scale_peak):
                    n = (t - st) / max(1e-6, en - st)
                    n = max(0.0, min(1.0, n))
                    return 1.0 + (peak - 1.0) * self._soft_bounce(n)

                active = (
                    TextClip(line_text, fontsize=font_size, font=font_name, color=fill_color, kerning=int(style["line_kerning"]), method="caption", size=(max_caption_w, None), align="center", stroke_color="#000000", stroke_width=stroke_width)
                    .set_opacity(1.0)
                    .resize(scale_fn)
                    .set_position(("center", y))
                    .set_start(word_start)
                    .set_end(word_end)
                    .crossfadein(fade_in_t)
                    .crossfadeout(fade_out_t)
                )
                glow = (
                    TextClip(line_text, fontsize=font_size, font=font_name, color=glow_color if preset != "neon" else "#71A6FF", kerning=int(style["line_kerning"]), method="caption", size=(max_caption_w, None), align="center", stroke_color=glow_color, stroke_width=max(1, stroke_width - 1))
                    .set_opacity(float(style["glow_opacity"]))
                    .set_position(("center", y))
                    .set_start(word_start)
                    .set_end(word_end)
                )
                clips.extend([glow, active])

        if debug_layout:
            debug_text = f"SAFE {safe['left']}:{safe['top']} {safe['right']}:{safe['bottom']} | MAXW {max_caption_w}"
            debug = TextClip(debug_text, fontsize=24, font=font_name, color="#00FF9A", method="caption", size=(video_w, None), align="center")
            clips.append(debug.set_position(("center", safe["top"] // 2)).set_start(0).set_end(max(float(words[-1].get("end", 1.0)), 1.0)).set_opacity(0.55))

        return clips
