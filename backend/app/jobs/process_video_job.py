import os
import time
import subprocess
import json
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.services.whisper_service import transcribe_video
from app.services.hook_detector import detect_hooks
from app.services.ffmpeg_service import cut_clip, apply_broll_overlay
from app.services.vertical_render_service import render_vertical_clip, render_dual_region_clip, render_semi_auto_vertical
from app.services.broll_engine import BRollEngine
from app.services.social_metadata_service import generate_social_metadata
from app.services.ai_metadata_service import apply_metadata_to_clip, no_ai_metadata
from app.data.timeline_state import set_timeline_state, save_timeline_state_for_analysis
from app.services.analysis_cache_service import load_analysis_cache, save_analysis_cache
from app.services.chunk_processing_service import (
    analyze_chunks_parallel,
    is_long_video,
    merge_chunk_analysis,
    resolve_chunk_duration,
    split_video_into_chunks,
)
from app.services.performance_profiler import PerformanceProfiler

INVALID_SAVE_FOLDER_MESSAGE = "Escolha uma pasta real para salvar os clipes."
_PLACEHOLDER_SAVE_FOLDER_TOKENS = ("<user>", "{user}", "%user%", "$user", "username", "your_username")


def _sanitize_auto_save_dir(auto_save_dir: str | None) -> str | None:
    if auto_save_dir is None:
        return None
    normalized = auto_save_dir.strip()
    if not normalized:
        return None
    lowered = normalized.lower()
    if "<" in normalized or ">" in normalized or any(token in lowered for token in _PLACEHOLDER_SAVE_FOLDER_TOKENS):
        raise ValueError(INVALID_SAVE_FOLDER_MESSAGE)
    if not os.path.isabs(normalized):
        print(f"[INVALID_AUTO_SAVE_DIR_FALLBACK] Caminho relativo ignorado para auto_save_dir: '{normalized}'.")
        return None
    return os.path.abspath(os.path.expanduser(normalized))


def _friendly_clip_filename(idx: int, hook: dict, source_path: str) -> str:
    score = int(round(float(hook.get("viral_score", 0) or 0)))
    extension = os.path.splitext(source_path)[1] or ".mp4"
    return f"clip_{idx + 1:02d}_score_{score}{extension}"


def _copy_rendered_clip_to_export(final_path: str, auto_save_dir: str | None, analysis_id: str, idx: int, hook: dict) -> tuple[str | None, str | None]:
    if not auto_save_dir:
        return None, None

    try:
        export_dir = os.path.join(auto_save_dir, analysis_id)
        os.makedirs(export_dir, exist_ok=True)
        export_path = os.path.join(export_dir, _friendly_clip_filename(idx, hook, final_path))
        shutil.copy2(final_path, export_path)
        print(f"[EXPORT_COPY_SUCCESS] analysis_id={analysis_id} clip_index={idx} export_path={export_path}")
        return export_path, export_path
    except Exception as error:
        print(f"[EXPORT_COPY_FAILED] analysis_id={analysis_id} clip_index={idx} source={final_path} error={error}")
        return None, None



def _to_media_url(path: str | None) -> str | None:
    if not path:
        return None
    rel_path = os.path.normpath(path).replace(os.path.normpath("app/clips") + os.sep, "", 1)
    return f"/media/{rel_path.replace(os.sep, '/')}"


def _clip_response_item(hook: dict, index: int) -> dict:
    return {
        "id": f"clip-{index}",
        "label": f"Clip {index + 1}",
        "start": hook["start"],
        "end": hook["end"],
        "duration": round(hook["end"] - hook["start"], 2),
        "clip_path": _to_media_url(hook["clip_path"]),
        "raw_clip_path": _to_media_url(hook.get("raw_clip_path", hook["clip_path"])),
        "final_video": _to_media_url(hook["final_clip"]),
        "export_path": hook.get("export_path"),
        "local_export_path": hook.get("local_export_path"),
        "viral_score": hook["viral_score"],
        "hook_score": hook.get("hook_score", hook["viral_score"]),
        "retention_score": hook.get("retention_score"),
        "emotion_score": hook.get("emotional_score"),
        "title": hook.get("title_suggestion", ""),
        "caption": hook.get("caption_suggestion", ""),
        "description": hook.get("description_suggestion", ""),
        "hashtags": hook.get("hashtags", []),
        "emotion": hook.get("emotion", "Não analisado"),
        "category": hook.get("category", "Auto"),
        "viral_reason": hook.get("viral_reason", ""),
        "title_options": hook.get("title_options", []),
        "metadata_status": hook.get("metadata_status", "no_ai"),
        "metadata_provider": hook.get("metadata_provider", "none"),
    }


def _persist_ready_timeline_state(analysis_id: str, ready_clips: list[dict], timeline_broll: list, timeline_cuts: list, render_mode: str, dual_region_config: dict | None) -> None:
    clips = [_clip_response_item(clip, index) for index, clip in enumerate(ready_clips)]
    first_video = clips[0]["final_video"] if clips else None
    duration = max((clip.get("end", 0) for clip in ready_clips), default=0.0)
    state = {
        "renderMode": "preview",
        "analysisId": analysis_id,
        "videoUrl": first_video,
        "previewVideoUrl": first_video,
        "exportVideoUrl": first_video,
        "duration": duration,
        "clips": clips,
        "hooks": [{"id": f"hook-{index}", "label": "Hook", "start": clip["start"], "end": clip["end"], "text": clip.get("text", "")} for index, clip in enumerate(ready_clips)],
        "broll": timeline_broll,
        "cuts": timeline_cuts,
        "renderQueue": [],
        "render_mode": render_mode,
        "status": "background_processing",
        "dual_regions": dual_region_config,
        "dual_region_config": dual_region_config,
        "semi_auto": None,
        "semi_auto_config": None,
    }
    set_timeline_state(state)
    save_timeline_state_for_analysis(analysis_id, state)

def _probe_audio_stream(video_path: str):
    probe_cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_name,sample_rate",
        "-of", "json",
        video_path,
    ]
    proc = subprocess.run(probe_cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        print(f"[PROXY AUDIO PROBE ERROR] returncode={proc.returncode}")
        return None
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return None
    streams = data.get("streams", [])
    return streams[0] if streams else None


def _proxy_audio_is_whisper_safe(video_path: str) -> bool:
    stream = _probe_audio_stream(video_path)
    if not stream:
        return False
    codec = (stream.get("codec_name") or "").lower()
    sample_rate = str(stream.get("sample_rate") or "")
    return codec == "aac" and sample_rate == "16000"


def _emit_pipeline_event(event_logger, event_type: str, analysis_id: str, started_at: float, clip_count: int = 0, **extra):
    payload = {
        "event": event_type,
        "analysis_id": analysis_id,
        "time": time.time(),
        "clip_count": clip_count,
        "total_time": round(time.perf_counter() - started_at, 3),
        **extra,
    }
    print(f"[{event_type}] analysis_id={analysis_id} clips={clip_count} total_time={payload['total_time']}")
    if event_logger:
        event_logger(payload)


def _run_ffprobe(video_path: str) -> dict:
    cmd = ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", video_path]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return {"error": proc.stderr}
    data = json.loads(proc.stdout or "{}")
    video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    return {
        "duration": float(data.get("format", {}).get("duration") or 0),
        "fps": video_stream.get("r_frame_rate"),
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
    }


def _generate_proxy(source_video_path: str, proxy_video_path: str, profiler: PerformanceProfiler) -> str:
    if os.path.exists(proxy_video_path):
        print("[PROXY CACHE HIT]")
        return proxy_video_path
    profiler.start_timer("proxy_generation")
    print("[PROXY CACHE MISS]")
    proxy_cmd = [
        "ffmpeg", "-y", "-hwaccel", "auto", "-threads", "4", "-extra_hw_frames", "8",
        "-i", source_video_path,
        "-map", "0:v:0", "-map", "0:a:0?",
        "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "h264_nvenc", "-preset", "p1", "-tune", "ll",
        "-c:a", "aac", "-b:a", "128k", "-ar", "16000", "-ac", "1", "-shortest",
        proxy_video_path,
    ]
    subprocess.run(proxy_cmd, check=True)
    profiler.end_timer("proxy_generation")
    return proxy_video_path


def _extract_audio(source_video_path: str, audio_path: str) -> str:
    if os.path.exists(audio_path):
        print("[AUDIO CACHE HIT]")
        return audio_path
    subprocess.run(["ffmpeg", "-y", "-i", source_video_path, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", audio_path], check=False)
    return audio_path


def _generate_waveform(audio_or_video_path: str, waveform_path: str) -> str:
    if os.path.exists(waveform_path):
        print("[WAVEFORM CACHE HIT]")
        return waveform_path
    subprocess.run(["ffmpeg", "-y", "-i", audio_or_video_path, "-filter_complex", "aformat=channel_layouts=mono,showwavespic=s=1200x180", "-frames:v", "1", waveform_path], check=False)
    return waveform_path


def _detect_silence(audio_or_video_path: str) -> list[dict]:
    proc = subprocess.run(["ffmpeg", "-i", audio_or_video_path, "-af", "silencedetect=noise=-30dB:d=0.35", "-f", "null", "-"], capture_output=True, text=True, check=False)
    events = []
    for line in (proc.stderr or "").splitlines():
        if "silence_start" in line:
            events.append({"type": "start", "time": line.rsplit(" ", 1)[-1]})
        elif "silence_end" in line:
            events.append({"type": "end", "raw": line})
    return events


def _detect_scene_changes(video_path: str) -> list[dict]:
    proc = subprocess.run(["ffmpeg", "-i", video_path, "-vf", "select='gt(scene,0.35)',showinfo", "-f", "null", "-"], capture_output=True, text=True, check=False)
    return [{"raw": line} for line in (proc.stderr or "").splitlines() if "pts_time" in line][:500]


def _speech_timestamps(transcription: dict) -> list[dict]:
    return [{"start": s.get("start", 0), "end": s.get("end", 0)} for s in transcription.get("segments", [])]


def process_video(video_path, original_video_path=None, proxy_video_path=None, output_dir="app/clips", render_mode="ai_tracking", dual_region_config=None, min_clip_length=30, max_clip_length=90, max_clips=25, min_score=0.45, overlap_tolerance=0.6, step_logger=None, auto_save_dir=None, event_logger=None):
    os.makedirs(output_dir, exist_ok=True)
    auto_save_dir = _sanitize_auto_save_dir(auto_save_dir)
    if auto_save_dir:
        os.makedirs(auto_save_dir, exist_ok=True)
    log = step_logger or (lambda _msg: None)
    started_at = time.perf_counter()
    analysis_id = os.path.basename(output_dir.rstrip("/"))
    fast_pipeline = os.getenv("FAST_PIPELINE", "true").lower() in {"1", "true", "yes", "on"}
    first_batch_size = 5 if fast_pipeline else min(10, max_clips)
    profiler = PerformanceProfiler(report_path=os.path.join(output_dir, "performance_report.json"))
    profiler.record_gpu_info()
    profiler.start_timer("total_pipeline")
    source_video_path = original_video_path or video_path
    proxy_video_path = proxy_video_path or os.path.join(output_dir, "proxy_720p.mp4")
    audio_path = os.path.join(output_dir, "audio_16k.wav")
    waveform_path = os.path.join(output_dir, "waveform.png")
    cache = load_analysis_cache(analysis_id) or {}

    _emit_pipeline_event(event_logger, "PIPELINE_STAGE_STARTED", analysis_id, started_at, stage="ingestion")
    with ThreadPoolExecutor(max_workers=4) as ingest_pool:
        futures = {
            "probe": ingest_pool.submit(_run_ffprobe, source_video_path),
            "proxy": ingest_pool.submit(_generate_proxy, source_video_path, proxy_video_path, profiler),
            "audio": ingest_pool.submit(_extract_audio, source_video_path, audio_path),
            "waveform": ingest_pool.submit(_generate_waveform, source_video_path, waveform_path),
        }
        ingest_results = {name: future.result() for name, future in futures.items()}
    _emit_pipeline_event(event_logger, "PIPELINE_STAGE_FINISHED", analysis_id, started_at, stage="ingestion")

    whisper_audio_source = proxy_video_path if _proxy_audio_is_whisper_safe(proxy_video_path) else source_video_path
    _emit_pipeline_event(event_logger, "PIPELINE_STAGE_STARTED", analysis_id, started_at, stage="transcription")
    with ThreadPoolExecutor(max_workers=4) as analysis_pool:
        silence_future = analysis_pool.submit(lambda: cache.get("silence") or _detect_silence(audio_path if os.path.exists(audio_path) else whisper_audio_source))
        scene_future = analysis_pool.submit(lambda: cache.get("scene_changes") or _detect_scene_changes(proxy_video_path))
        if cache.get("transcription"):
            transcription = cache["transcription"]
            print("[TRANSCRIPTION CACHE HIT]")
        else:
            log("[STEP 5 - TRANSCRIPTION START]")
            transcription = transcribe_video(whisper_audio_source, profiler=profiler)
            log("[STEP 6 - TRANSCRIPTION FINISH]")
        silence = silence_future.result()
        scene_changes = scene_future.result()
    speech = cache.get("speech_timestamps") or _speech_timestamps(transcription)
    _emit_pipeline_event(event_logger, "PIPELINE_STAGE_FINISHED", analysis_id, started_at, stage="transcription")

    _emit_pipeline_event(event_logger, "PIPELINE_STAGE_STARTED", analysis_id, started_at, stage="fast_detection")
    if cache.get("hooks"):
        hooks = cache["hooks"]
        print("[HOOK CACHE HIT]")
    else:
        hooks = detect_hooks(transcription, min_duration=min_clip_length, max_duration=max_clip_length, max_clips=max(80, max_clips), min_score=min_score, overlap_tolerance=overlap_tolerance)
    hooks = sorted(hooks, key=lambda h: h.get("viral_score", 0), reverse=True)[:max_clips]
    save_analysis_cache(analysis_id, {**cache, "transcription": transcription, "hooks": hooks, "waveform": waveform_path, "speech_timestamps": speech, "scene_changes": scene_changes, "silence": silence, "probe": ingest_results.get("probe"), "proxy": proxy_video_path})
    _emit_pipeline_event(event_logger, "PIPELINE_STAGE_FINISHED", analysis_id, started_at, len(hooks), stage="fast_detection")

    broll_engine = BRollEngine()
    generated_clips = [None] * len(hooks)
    timeline_broll, timeline_cuts = [], []
    max_parallel_renders = max(1, int(os.getenv("MAX_PARALLEL_RENDERS", "2")))

    def _render(idx, hook):
        raw = cut_clip(proxy_video_path, hook["start"], hook["end"], f"raw_clip_{idx}.mp4", output_dir=output_dir)
        processed = raw
        if render_mode == "ai_tracking":
            processed = render_vertical_clip(raw, transcription["segments"], os.path.join(output_dir, f"clip_{idx}.mp4"), speaker_segments=transcription.get("speaker_segments", []), tracking_video_path=proxy_video_path, original_video_path=source_video_path)
        elif render_mode == "dual_region" and dual_region_config:
            processed = os.path.join(output_dir, f"clip_{idx}_dual.mp4"); render_dual_region_clip(raw, processed, dual_region_config)
        elif render_mode == "semi_auto":
            processed = os.path.join(output_dir, f"clip_{idx}_semi_auto.mp4"); render_semi_auto_vertical(raw, processed)
        seg_timeline = broll_engine.build_timeline([s for s in transcription["segments"] if hook["start"] <= s.get("start", 0) <= hook["end"]])
        final = apply_broll_overlay(processed, seg_timeline, f"clip_{idx}_final.mp4", output_dir=output_dir, quality_profile="export")
        export_path, local_export_path = _copy_rendered_clip_to_export(final, auto_save_dir, analysis_id, idx, hook)
        clip = apply_metadata_to_clip({"raw_clip_path": raw, "clip_path": processed, "final_clip": final, "export_path": export_path, "local_export_path": local_export_path, **hook, "title_suggestion": "", "caption_suggestion": "", "description_suggestion": "", "hashtags": [], "emotion": "Não analisado", "category": "Auto", "viral_reason": "", "title_options": [], "broll_timeline": seg_timeline}, no_ai_metadata(hook, idx))
        return idx, clip

    _emit_pipeline_event(event_logger, "PIPELINE_STAGE_STARTED", analysis_id, started_at, stage="top_clip_render")
    with ThreadPoolExecutor(max_workers=max_parallel_renders) as render_pool:
        futures = [render_pool.submit(_render, i, h) for i, h in enumerate(hooks)]
        first_clip_announced = False
        for future in as_completed(futures):
            idx, clip = future.result()
            generated_clips[idx] = clip
            ready = [c for c in generated_clips if c]
            timeline_cuts.append({"id": f"cut-{idx}", "label": f"Cut {idx + 1}", "start": clip["start"], "end": clip["start"] + 0.1})
            _emit_pipeline_event(event_logger, "CLIP_RENDERED", analysis_id, started_at, len(ready), clip_index=idx, clip=clip)
            if not first_clip_announced:
                first_clip_announced = True
                _persist_ready_timeline_state(analysis_id, ready, timeline_broll, timeline_cuts, render_mode, dual_region_config)
                _emit_pipeline_event(event_logger, "FIRST_CLIP_READY", analysis_id, started_at, len(ready), clip=clip)
                _emit_pipeline_event(event_logger, "EDITOR_READY", analysis_id, started_at, len(ready))
            if len(ready) == first_batch_size:
                _emit_pipeline_event(event_logger, "BACKGROUND_PROCESSING", analysis_id, started_at, len(ready), message="Editor can be used while remaining clips and metadata continue.")
    clips = [c for c in generated_clips if c]
    _persist_ready_timeline_state(analysis_id, clips, timeline_broll, timeline_cuts, render_mode, dual_region_config)
    _emit_pipeline_event(event_logger, "BACKGROUND_FINISHED", analysis_id, started_at, len(clips))
    profiler.end_timer("total_pipeline")
    profiler.finalize()
    return {"text": " ".join([s.get("text", "") for s in transcription.get("segments", [])]), "hooks": clips, "status": "completed", "timeline": {"broll": timeline_broll, "cuts": timeline_cuts}, "pipeline": {"fast_pipeline": fast_pipeline, "first_batch_size": first_batch_size}}
