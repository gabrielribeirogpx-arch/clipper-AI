from typing import Dict, List

from app.services.emotion_analysis import analyze_emotion
from app.services.retention_engine import analyze_retention


def _average_wps(segments: List[Dict]) -> float:
    total_duration = 0.0
    total_words = 0

    for seg in segments:
        text = seg.get("text", "").strip()
        words = len(text.split())
        duration = max(seg["end"] - seg["start"], 0.01)
        total_duration += duration
        total_words += words

    if total_duration <= 0:
        return 0.0

    return total_words / total_duration


def compute_viral_score(window_segments: List[Dict], baseline_wps: float) -> Dict:
    emotion_data = analyze_emotion(window_segments, baseline_wps)
    retention_data = analyze_retention(window_segments)

    emotional_score = emotion_data["emotional_score"]
    retention_score = retention_data["retention_score"]

    # Viral final privilegia retenção + emoção com leve boost para equilíbrio.
    balance_bonus = 10 if min(emotional_score, retention_score) > 65 else 0

    viral_score = min(
        100.0,
        0.55 * retention_score + 0.45 * emotional_score + balance_bonus,
    )

    return {
        "emotional_score": emotional_score,
        "retention_score": retention_score,
        "viral_score": round(viral_score, 2),
        "analysis": {
            "emotion_signals": emotion_data["signals"],
            "retention_signals": retention_data["signals"],
            "baseline_wps": round(baseline_wps, 3),
        },
    }


def rank_hooks(hooks: List[Dict], max_results: int = 5) -> List[Dict]:
    ranked = sorted(hooks, key=lambda h: h["viral_score"], reverse=True)
    return ranked[:max_results]


def detect_and_rank_hooks(segments: List[Dict], min_duration: int = 30, max_duration: int = 90) -> List[Dict]:
    hooks = []
    baseline_wps = _average_wps(segments)
    last_end = 0.0

    for i, segment in enumerate(segments):
        duration = segment["end"] - segment["start"]
        if duration < 3:
            continue
        if segment["start"] < last_end:
            continue

        start = max(segment["start"] - 1.5, 0)
        dynamic_window = max(min_duration, min(max_duration, int(duration * 4)))
        end = min(start + dynamic_window, segments[-1]["end"])

        window_segments = [
            seg for seg in segments
            if seg["start"] < end and seg["end"] > start
        ]

        if not window_segments:
            continue

        score_data = compute_viral_score(window_segments, baseline_wps)

        hook = {
            "start": round(start, 2),
            "end": round(end, 2),
            "text": " ".join(seg.get("text", "").strip() for seg in window_segments).strip(),
            "source_segment_index": i,
            "title": (segment.get("text", "").strip()[:58] + "...") if len(segment.get("text", "").strip()) > 58 else segment.get("text", "").strip(),
            **score_data,
        }

        hooks.append(hook)
        last_end = end

    return rank_hooks(hooks)
