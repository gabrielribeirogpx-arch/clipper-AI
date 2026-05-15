import math
import re
from typing import Dict, List


STRONG_WORDS = {
    "nunca", "sempre", "agora", "segredo", "chocante", "absurdo",
    "inacreditável", "proibido", "urgente", "erro", "milagre", "bomba",
    "crise", "muda", "transforma", "imediato", "explodiu"
}

IMPACT_PHRASES = {
    "presta atenção", "ninguém te conta", "vou te mostrar",
    "isso muda tudo", "olha isso", "não cometa esse erro",
    "essa é a verdade", "anota isso"
}


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _normalize(value: float, max_value: float) -> float:
    if max_value <= 0:
        return 0.0
    return max(0.0, min(1.0, value / max_value))


def analyze_emotion(window_segments: List[Dict], baseline_wps: float) -> Dict:
    """Calcula score emocional com base em sinais de linguagem e ritmo."""

    text = " ".join(seg.get("text", "") for seg in window_segments).strip()
    words = [w.lower() for w in re.findall(r"\w+", text, flags=re.UNICODE)]

    duration = max(window_segments[-1]["end"] - window_segments[0]["start"], 0.1)
    words_count = len(words)
    wps = _safe_div(words_count, duration)

    exclamation_count = text.count("!")
    uppercase_tokens = [token for token in text.split() if token.isupper() and len(token) > 2]
    strong_hits = sum(1 for word in words if word in STRONG_WORDS)
    phrase_hits = sum(1 for phrase in IMPACT_PHRASES if phrase in text.lower())
    question_count = text.count("?")

    pace_delta = max(0.0, wps - baseline_wps)
    pace_signal = _normalize(pace_delta, 1.5)

    score = (
        0.25 * _normalize(strong_hits, 6)
        + 0.2 * _normalize(exclamation_count, 5)
        + 0.15 * _normalize(len(uppercase_tokens), 4)
        + 0.2 * _normalize(phrase_hits, 3)
        + 0.1 * _normalize(question_count, 4)
        + 0.1 * pace_signal
    )

    return {
        "emotional_score": round(score * 100, 2),
        "signals": {
            "strong_words": strong_hits,
            "impact_phrases": phrase_hits,
            "questions": question_count,
            "exclamations": exclamation_count,
            "pace_delta": round(pace_delta, 3),
            "speech_wps": round(wps, 3),
            "contains_shout": len(uppercase_tokens) > 0,
        },
    }
