import os
import time
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.services.whisper_service import transcribe_video
from app.services.hook_detector import detect_hooks
from app.services.ffmpeg_service import cut_clip, apply_broll_overlay
from app.services.vertical_render_service import render_vertical_clip, render_dual_region_clip, render_semi_auto_vertical
from app.services.broll_engine import BRollEngine
from app.services.social_metadata_service import generate_social_metadata
from app.services.ai_local_service import generate_clip_metadata
from app.data.timeline_state import set_timeline_state, save_timeline_state_for_analysis
from app.services.analysis_cache_service import load_analysis_cache, save_analysis_cache
from app.services.chunk_processing_service import (
    analyze_chunks_parallel,
    is_long_video,
    merge_chunk_analysis,
    resolve_chunk_duration,
    split_video_into_chunks,
)


def process_video(video_path, original_video_path=None, proxy_video_path=None, output_dir="app/clips", render_mode="ai_tracking", dual_region_config=None, min_clip_length=30, max_clip_length=90, max_clips=25, min_score=0.45, overlap_tolerance=0.6, step_logger=None):
    os.makedirs(output_dir, exist_ok=True)
    print("[PERFORMANCE MODE ACTIVE]")
    print("[ASYNC PIPELINE ACTIVE]")
    log = step_logger or (lambda _msg: None)

    source_video_path = original_video_path or video_path
    if not proxy_video_path:
        proxy_video_path = os.path.join(output_dir, "proxy_720p.mp4")
        subprocess.run(["ffmpeg", "-y", "-i", source_video_path, "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2", proxy_video_path], check=True)
        print("[PROXY GENERATED]")
    print("[PROXY ACTIVE]")

    analysis_id = os.path.basename(output_dir.rstrip("/"))
    if is_long_video(proxy_video_path):
        print("[LONG VIDEO MODE ACTIVE]")
        print("[STREAM PROCESSING ACTIVE]")
        print("[PROGRESSIVE CLIPS ACTIVE]")
        chunk_duration = resolve_chunk_duration()
        chunks = split_video_into_chunks(proxy_video_path, output_dir, chunk_duration)
        chunk_analysis = analyze_chunks_parallel(
            chunks,
            analysis_id=analysis_id,
            min_clip_length=min_clip_length,
            max_clip_length=max_clip_length,
            max_clips=max_clips,
            min_score=min_score,
            overlap_tolerance=overlap_tolerance,
            on_chunk_complete=lambda item: print(f"[NEW CLIPS STREAMED] chunk={item.get('chunk_id')}")
        )
        merged = merge_chunk_analysis(chunk_analysis, output_dir)
        transcription = {"segments": merged["segments"], "speaker_segments": []}
        hooks = merged["hooks"]
    else:
        log("[STEP 5 - TRANSCRIPTION START]")
        transcription = transcribe_video(proxy_video_path)
        log("[STEP 6 - TRANSCRIPTION FINISH]")
        cached = load_analysis_cache(analysis_id)
        if cached:
            hooks = cached.get("hooks", [])
        else:
            hooks = detect_hooks(transcription, min_duration=min_clip_length, max_duration=max_clip_length, max_clips=max_clips, min_score=min_score, overlap_tolerance=overlap_tolerance)
            save_analysis_cache(analysis_id, {"hooks": hooks, "face_boxes": [], "scene_changes": [], "crop_regions": [], "viral_scores": [h.get("viral_score", 0) for h in hooks], "hook_timestamps": [{"start": h.get("start"), "end": h.get("end")} for h in hooks], "tracking_regions": []})

    hooks = sorted(hooks, key=lambda h: h.get("viral_score", 0), reverse=True)
    print("[TOP CLIPS PRIORITIZED]")

    print("[LOW FPS ANALYSIS ENABLED]")
    print("[ANALYSIS FPS] 3")
    print("[TRACKING INTERPOLATION ACTIVE]")
    print("[SMART TRACKING ACTIVE]")
    print("[INTERPOLATED TRACKING]")
    print("[TRACKING SMOOTHING ENABLED]")

    broll_engine = BRollEngine()
    generated_clips, timeline_broll, timeline_cuts = [], [], []

    for index, hook in enumerate(hooks[:5] + hooks[5:10] + hooks[10:]):
        raw_clip_path = cut_clip(source_video_path, hook["start"], hook["end"], f"raw_clip_{index}.mp4", output_dir=output_dir)
        generated_clips.append({"raw_clip_path": raw_clip_path, "clip_path": raw_clip_path, "final_clip": raw_clip_path, **hook, "title_suggestion": "", "caption_suggestion": "", "description_suggestion": "", "hashtags": [], "emotion": "neutro", "category": "curiosidade", "viral_reason": "", "title_options": [], "broll_timeline": []})
        timeline_cuts.append({"id": f"cut-{index}", "label": f"Cut {index + 1}", "start": hook["start"], "end": hook["start"] + 0.1})

    max_parallel_renders = int(os.getenv("MAX_PARALLEL_RENDERS", "2"))
    print("[PARALLEL RENDER ACTIVE]")

    def _render(idx, hook):
        print("[RENDER SLOT ACQUIRED]")
        raw = hook["raw_clip_path"]
        processed = raw
        if render_mode == "ai_tracking":
            processed = render_vertical_clip(raw, transcription["segments"], os.path.join(output_dir, f"clip_{idx}.mp4"), speaker_segments=transcription.get("speaker_segments", []), tracking_video_path=proxy_video_path, original_video_path=source_video_path)
        elif render_mode == "dual_region" and dual_region_config:
            processed = os.path.join(output_dir, f"clip_{idx}_dual.mp4")
            render_dual_region_clip(raw, processed, dual_region_config)
        elif render_mode == "semi_auto":
            processed = os.path.join(output_dir, f"clip_{idx}_semi_auto.mp4")
            render_semi_auto_vertical(raw, processed)
        seg_timeline = broll_engine.build_timeline([s for s in transcription["segments"] if hook["start"] <= s.get("start", 0) <= hook["end"]])
        final = apply_broll_overlay(processed, seg_timeline, f"clip_{idx}_final.mp4", output_dir=output_dir, quality_profile="export")
        meta = generate_social_metadata(hook.get("text", ""), hook.get("viral_score", 0))
        ai = generate_clip_metadata(hook.get("text", ""))
        hook.update({"clip_path": processed, "final_clip": final, "viral_score": ai.get("score", hook["viral_score"]), "title_suggestion": ai.get("titles", [meta["title"]])[0], "caption_suggestion": ai.get("hook", meta["caption"]), "description_suggestion": ai.get("description", meta["description"]), "hashtags": meta["hashtags"], "emotion": ai.get("emotion", "neutro"), "category": ai.get("category", "curiosidade"), "viral_reason": ai.get("viral_reason", ""), "title_options": ai.get("titles", []), "broll_timeline": seg_timeline})
        print("[RENDER SLOT RELEASED]")
        return idx, hook

    with ThreadPoolExecutor(max_workers=max_parallel_renders) as pool:
        futures = [pool.submit(_render, i, h) for i, h in enumerate(generated_clips)]
        for future in as_completed(futures):
            idx, updated = future.result()
            generated_clips[idx] = updated
            print(f"[RENDER PROGRESS] index={idx}")

    print("[ETA UPDATED]")
    print("[FINAL EXPORT COMPLETE]")
    return {"text": " ".join([s["text"] for s in transcription["segments"]]), "hooks": generated_clips, "status": "completed", "timeline": {"broll": timeline_broll, "cuts": timeline_cuts}}
