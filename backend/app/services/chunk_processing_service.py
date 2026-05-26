from __future__ import annotations

import gc
import json
import os
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

from app.services.analysis_cache_service import load_analysis_cache, save_analysis_cache
from app.services.hook_detector import detect_hooks
from app.services.whisper_service import transcribe_video

DEFAULT_CHUNK_DURATION = int(os.getenv("DEFAULT_CHUNK_DURATION", "300"))
SUPPORTED_CHUNK_DURATIONS = {180, 300, 600}
LONG_VIDEO_MODE_THRESHOLD_SECONDS = int(os.getenv("LONG_VIDEO_MODE_THRESHOLD_SECONDS", str(2 * 3600)))
MAX_PARALLEL_CHUNKS = int(os.getenv("MAX_PARALLEL_CHUNKS", "4"))


def _ffprobe_duration(video_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", video_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return 0.0
    try:
        return float((proc.stdout or "0").strip())
    except ValueError:
        return 0.0


def resolve_chunk_duration() -> int:
    if DEFAULT_CHUNK_DURATION in SUPPORTED_CHUNK_DURATIONS:
        return DEFAULT_CHUNK_DURATION
    return 300


def is_long_video(video_path: str) -> bool:
    return _ffprobe_duration(video_path) > LONG_VIDEO_MODE_THRESHOLD_SECONDS


def split_video_into_chunks(video_path: str, output_dir: str, chunk_duration: int) -> list[dict[str, Any]]:
    chunks_dir = Path(output_dir) / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    print("[CHUNK PROCESSING ACTIVE]")
    output_pattern = str(chunks_dir / "chunk_%04d.mp4")
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-c", "copy",
        "-f", "segment",
        "-segment_time", str(chunk_duration),
        "-reset_timestamps", "1",
        output_pattern,
    ]
    subprocess.run(cmd, check=True)

    chunk_files = sorted(chunks_dir.glob("chunk_*.mp4"))
    chunks: list[dict[str, Any]] = []
    offset = 0.0
    for idx, chunk_file in enumerate(chunk_files, start=1):
        duration = _ffprobe_duration(str(chunk_file))
        chunks.append({
            "index": idx,
            "chunk_id": f"chunk_{idx:04d}",
            "path": str(chunk_file),
            "offset": offset,
            "duration": duration,
        })
        print(f"[CHUNK QUEUED] id=chunk_{idx:04d}")
        offset += duration
    return chunks


def _analyze_single_chunk(args: tuple[dict[str, Any], str, int, int, int, float, float]) -> dict[str, Any]:
    chunk, analysis_id, min_clip_length, max_clip_length, max_clips, min_score, overlap_tolerance = args
    chunk_cache_key = f"{analysis_id}_{chunk['chunk_id']}"
    cached = load_analysis_cache(chunk_cache_key)
    if cached:
        print(f"[CHUNK CACHE HIT] id={chunk['chunk_id']}")
        return cached

    print(f"[CHUNK START] id={chunk['chunk_id']}")
    transcription = transcribe_video(chunk["path"])
    hooks = detect_hooks(
        transcription,
        min_duration=min_clip_length,
        max_duration=max_clip_length,
        max_clips=max_clips,
        min_score=min_score,
        overlap_tolerance=overlap_tolerance,
    )
    for hook in hooks:
        hook["start"] = hook.get("start", 0.0) + chunk["offset"]
        hook["end"] = hook.get("end", 0.0) + chunk["offset"]

    payload = {
        "chunk_id": chunk["chunk_id"],
        "offset": chunk["offset"],
        "transcript": transcription.get("segments", []),
        "hooks": hooks,
        "emotion_peaks": [],
        "silence_ranges": [],
        "viral_candidates": hooks,
        "crop_regions": [],
        "scene_changes": [],
        "speaker_segments": transcription.get("speaker_segments", []),
    }
    save_analysis_cache(chunk_cache_key, payload)
    print(f"[CHUNK COMPLETE] id={chunk['chunk_id']}")
    return payload


def analyze_chunks_parallel(
    chunks: list[dict[str, Any]],
    analysis_id: str,
    min_clip_length: int,
    max_clip_length: int,
    max_clips: int,
    min_score: float,
    overlap_tolerance: float,
    on_chunk_complete: Callable[[dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    print("[PARALLEL CHUNK ANALYSIS ACTIVE]")
    args = [
        (chunk, analysis_id, min_clip_length, max_clip_length, max_clips, min_score, overlap_tolerance)
        for chunk in chunks
    ]
    results: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=min(MAX_PARALLEL_CHUNKS, max(1, len(args)))) as pool:
        futures = [pool.submit(_analyze_single_chunk, arg) for arg in args]
        for future in as_completed(futures):
            chunk_result = future.result()
            results.append(chunk_result)
            if on_chunk_complete:
                on_chunk_complete(chunk_result)
    return sorted(results, key=lambda x: x.get("offset", 0.0))


def merge_chunk_analysis(chunks_analysis: list[dict[str, Any]], output_dir: str) -> dict[str, Any]:
    merged_segments: list[dict[str, Any]] = []
    merged_hooks: list[dict[str, Any]] = []

    for item in chunks_analysis:
        chunk_id = item.get("chunk_id", "chunk_unknown")
        chunk_json = Path(output_dir) / f"analysis_{chunk_id}.json"
        chunk_json.write_text(json.dumps(item, ensure_ascii=False))
        print(f"[INCREMENTAL ANALYSIS UPDATE] {chunk_json.name}")

        offset = item.get("offset", 0.0)
        for segment in item.get("transcript", []):
            seg = dict(segment)
            seg["start"] = seg.get("start", 0.0) + offset
            seg["end"] = seg.get("end", 0.0) + offset
            merged_segments.append(seg)
        merged_hooks.extend(item.get("hooks", []))

    print("[FINAL MERGE COMPLETE]")
    print("[MEMORY CLEANUP ACTIVE]")
    gc.collect()
    return {"segments": merged_segments, "hooks": merged_hooks}
