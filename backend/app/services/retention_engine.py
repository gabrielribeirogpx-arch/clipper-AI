from typing import Dict, List


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _clamp(v: float, low: float, high: float) -> float:
    return max(low, min(high, v))


def analyze_retention(window_segments: List[Dict], ideal_min: int = 18, ideal_max: int = 38) -> Dict:
    """Heurística de retenção baseada em hook inicial, duração e punchline."""

    start = window_segments[0]["start"]
    end = window_segments[-1]["end"]
    duration = max(end - start, 0.1)

    window_text = " ".join(seg.get("text", "") for seg in window_segments).strip()
    lower_text = window_text.lower()
    first_20_chars = lower_text[:120]

    hook_triggers = ["você", "imagina", "segredo", "atenção", "olha", "como", "por quê", "porque"]
    strong_hook = any(trigger in first_20_chars for trigger in hook_triggers)

    punchline_triggers = ["resultado", "moral", "conclusão", "então", "por isso", "resumo", "final"]
    has_punchline = any(trigger in lower_text[-160:] for trigger in punchline_triggers)

    if duration < ideal_min:
        duration_fit = _safe_div(duration, ideal_min)
    elif duration > ideal_max:
        duration_fit = _safe_div(ideal_max, duration)
    else:
        duration_fit = 1.0

    pauses = 0
    for i in range(1, len(window_segments)):
        gap = window_segments[i]["start"] - window_segments[i - 1]["end"]
        if 0.35 <= gap <= 1.5:
            pauses += 1

    pause_score = _clamp(pauses / 4, 0.0, 1.0)

    score = (
        0.4 * duration_fit
        + 0.25 * (1.0 if strong_hook else 0.35)
        + 0.2 * (1.0 if has_punchline else 0.4)
        + 0.15 * pause_score
    )

    return {
        "retention_score": round(score * 100, 2),
        "signals": {
            "duration_seconds": round(duration, 2),
            "duration_fit": round(duration_fit, 3),
            "strong_initial_hook": strong_hook,
            "has_punchline": has_punchline,
            "dramatic_pauses": pauses,
        },
    }
