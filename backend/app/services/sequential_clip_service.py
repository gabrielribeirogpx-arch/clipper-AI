import math
import os
import re
import unicodedata


def _slugify_title(title: str, fallback: str, used: set[str] | None = None, max_length: int = 80) -> str:
    value = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode("ascii")
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", value)
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[\s-]+", "_", value).strip("_")[:max_length].strip("_")
    value = value or fallback
    if used is not None:
        base = value
        suffix = 2
        while value in used:
            value = f"{base}_{suffix}"
            suffix += 1
        used.add(value)
    return value


def _friendly_clip_filename(idx: int, hook: dict, source_path: str, used: set[str] | None = None) -> str:
    extension = os.path.splitext(source_path)[1] or ".mp4"
    fallback = f"parte_{idx + 1:02d}"
    title = hook.get("title") or hook.get("title_suggestion") or fallback
    slug = _slugify_title(str(title), fallback, used=used)
    return f"{idx + 1:02d}_{slug}{extension}"

def _segments_for_range(transcription: dict, start: float, end: float) -> list[dict]:
    return [s for s in transcription.get("segments", []) if float(s.get("start", 0) or 0) < end and float(s.get("end", 0) or 0) > start]


def _transcript_excerpt(transcription: dict, start: float, end: float) -> str:
    return " ".join(str(s.get("text", "")).strip() for s in _segments_for_range(transcription, start, end)).strip()


def _deterministic_title(text: str, index: int) -> str:
    words = re.findall(r"[\wÀ-ÿ]{4,}", (text or "").lower())
    stop = {"para", "como", "esse", "essa", "isso", "aqui", "mais", "muito", "sobre", "porque", "quando", "onde", "voce", "você", "entao", "então", "that", "this", "with", "from", "your", "have", "will"}
    selected = []
    for word in words:
        normalized = unicodedata.normalize("NFKD", word).encode("ascii", "ignore").decode("ascii")
        if normalized in stop or normalized in selected:
            continue
        selected.append(normalized)
        if len(selected) == 5:
            break
    return " ".join(selected).title() if selected else f"Parte {index + 1:02d}"


def _adjust_cut_to_sentence_boundary(planned: float, previous: float, source_end: float, segments: list[dict], max_adjust: float) -> float:
    candidates = []
    for segment in segments:
        end = float(segment.get("end", 0) or 0)
        text = str(segment.get("text", "")).strip()
        if previous < end < source_end and abs(end - planned) <= max_adjust and (not text or text[-1:] in ".!?…"):
            candidates.append(end)
    if not candidates:
        return planned
    adjusted = min(candidates, key=lambda value: abs(value - planned))
    return adjusted if adjusted > previous else planned


def _build_sequential_hooks(transcription: dict, source_start: float, source_end: float, clip_duration: int, adjust_to_sentence_boundaries: bool, avoid_short_last_clip: bool, generate_clip_titles: bool, max_adjust: float = 5.0) -> list[dict]:
    total = max(0.0, source_end - source_start)
    clip_duration = max(10, int(clip_duration or 60))
    print(f"[CLIP STRATEGY] strategy=sequential")
    print(f"[SEQUENTIAL PLAN] duration={round(total, 2)} clip_duration={clip_duration} estimated_clips={math.ceil(total / clip_duration) if clip_duration else 0}")
    ranges = []
    cursor = source_start
    while cursor < source_end - 0.001:
        planned_end = min(cursor + clip_duration, source_end)
        end = planned_end
        if adjust_to_sentence_boundaries and planned_end < source_end:
            end = _adjust_cut_to_sentence_boundary(planned_end, cursor, source_end, transcription.get("segments", []), max_adjust)
        ranges.append([round(cursor, 2), round(min(end, source_end), 2)])
        cursor = ranges[-1][1]
    if avoid_short_last_clip and len(ranges) >= 2 and (ranges[-1][1] - ranges[-1][0]) < clip_duration * 0.2:
        combined_start, combined_end = ranges[-2][0], ranges[-1][1]
        midpoint = round(combined_start + ((combined_end - combined_start) / 2), 2)
        ranges[-2] = [combined_start, midpoint]
        ranges[-1] = [midpoint, combined_end]
    hooks, used = [], set()
    for idx, (start, end) in enumerate(ranges):
        excerpt = _transcript_excerpt(transcription, start, end)
        title = _deterministic_title(excerpt, idx) if generate_clip_titles else f"Parte {idx + 1:02d}"
        filename = _friendly_clip_filename(idx, {"title": title}, ".mp4", used=used)
        print(f"[SEQUENTIAL RANGE] index={idx} start={start:g} end={end:g}")
        print(f"[CLIP TITLE] index={idx} title=\"{title}\"")
        print(f"[CLIP EXPORT NAME] index={idx} filename=\"{filename}\"")
        hooks.append({"clip_index": idx, "start": start, "end": end, "duration": round(end - start, 2), "viral_score": 0, "hook_score": 0, "strategy": "sequential", "title": title, "title_suggestion": title, "filename": filename, "transcript_excerpt": excerpt})
    gaps = overlaps = duplicates = 0
    seen = set()
    covered = sum(max(0, e - s) for s, e in ranges)
    for i, (s0, e0) in enumerate(ranges):
        duplicates += (round(s0, 2), round(e0, 2)) in seen
        seen.add((round(s0, 2), round(e0, 2)))
        if s0 >= e0 or s0 < source_start - .01 or e0 > source_end + .01:
            gaps += 1
        if i and abs(s0 - ranges[i - 1][1]) > .02:
            gaps += int(s0 > ranges[i - 1][1]); overlaps += int(s0 < ranges[i - 1][1])
    coverage = round((covered / total) * 100, 2) if total else 100
    print(f"[SEQUENTIAL VALIDATION] gaps={gaps} overlaps={overlaps} duplicates={duplicates} coverage={coverage}%")
    print(f"[SEQUENTIAL GENERATED] total_candidates={len(hooks)}")
    return hooks
