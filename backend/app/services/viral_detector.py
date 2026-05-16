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


def _normalize_score(score: float) -> float:
    return max(0.0, min(1.0, score / 100.0))


def _overlap_ratio(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    intersection = max(0.0, min(a_end, b_end) - max(a_start, b_start))
    shortest = max(min(a_end - a_start, b_end - b_start), 0.01)
    return intersection / shortest


def detect_and_rank_hooks(
    segments: List[Dict],
    min_duration: int = 30,
    max_duration: int = 90,
    max_clips: int = 25,
    min_score: float = 0.45,
    overlap_tolerance: float = 0.6,
) -> List[Dict]:
    hooks = []
    rejected = []
    baseline_wps = _average_wps(segments)

    if not segments:
        return []

    for i, segment in enumerate(segments):
        duration = segment["end"] - segment["start"]
        if duration < 1.5:
            continue

        start = max(segment["start"] - 1.5, 0)
        window_candidates = [
            max(min_duration, min(max_duration, int(duration * factor)))
            for factor in (2.5, 3.5, 5.0)
        ]

        for dynamic_window in window_candidates:
            end = min(start + dynamic_window, segments[-1]["end"])

            window_segments = [
                seg for seg in segments
                if seg["start"] < end and seg["end"] > start
            ]

            if not window_segments:
                rejected.append({"reason": "empty_window", "start": round(start, 2), "end": round(end, 2)})
                continue

            score_data = compute_viral_score(window_segments, baseline_wps)
            normalized_score = _normalize_score(score_data["viral_score"])
            if normalized_score < min_score:
                rejected.append({
                    "reason": "below_min_score",
                    "start": round(start, 2),
                    "end": round(end, 2),
                    "score": round(normalized_score, 3),
                })
                continue

            hook = {
                "start": round(start, 2),
                "end": round(end, 2),
                "text": " ".join(seg.get("text", "").strip() for seg in window_segments).strip(),
                "source_segment_index": i,
                "title": (segment.get("text", "").strip()[:58] + "...") if len(segment.get("text", "").strip()) > 58 else segment.get("text", "").strip(),
                "normalized_score": round(normalized_score, 3),
                **score_data,
            }

            hooks.append(hook)

    ranked = rank_hooks(hooks, max_results=max(max_clips * 4, 50))
    accepted = []

    for candidate in ranked:
        has_excessive_overlap = any(
            _overlap_ratio(candidate["start"], candidate["end"], selected["start"], selected["end"]) > overlap_tolerance
            for selected in accepted
        )
        if has_excessive_overlap:
            rejected.append({
                "reason": "overlap_rejection",
                "start": candidate["start"],
                "end": candidate["end"],
                "score": candidate["normalized_score"],
            })
            continue

        accepted.append(candidate)
        if len(accepted) >= max_clips:
            break

    print(
        f"[viral_detector] candidates={len(hooks)} accepted={len(accepted)} rejected={len(rejected)} "
        f"min_score={min_score} overlap_tolerance={overlap_tolerance} max_clips={max_clips}"
    )
    for idx, clip in enumerate(accepted[:10]):
        print(
            f"[viral_detector] accepted[{idx}] start={clip['start']} end={clip['end']} "
            f"score={clip['viral_score']} normalized={clip['normalized_score']}"
        )

    return accepted
