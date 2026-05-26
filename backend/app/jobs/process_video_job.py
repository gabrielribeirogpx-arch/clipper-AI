import os
import time
import subprocess

from app.services.whisper_service import transcribe_video
from app.services.hook_detector import detect_hooks
from app.services.ffmpeg_service import cut_clip, apply_broll_overlay
from app.services.vertical_render_service import render_vertical_clip, render_dual_region_clip, render_semi_auto_vertical
from app.services.broll_engine import BRollEngine
from app.services.social_metadata_service import generate_social_metadata
from app.services.ai_local_service import generate_clip_metadata
from app.data.timeline_state import set_timeline_state, save_timeline_state_for_analysis


def process_video(
    video_path,
    original_video_path: str | None = None,
    proxy_video_path: str | None = None,
    output_dir: str = "app/clips",
    render_mode: str = "ai_tracking",
    dual_region_config: dict | None = None,
    min_clip_length: int = 30,
    max_clip_length: int = 90,
    max_clips: int = 25,
    min_score: float = 0.45,
    overlap_tolerance: float = 0.6,
    step_logger=None,
):

    os.makedirs(output_dir, exist_ok=True)
    print(f"[CLIP OUTPUT PATH] {output_dir}")
    print(f"[PROCESS VIDEO RESOLVED MODE] render_mode={render_mode}")
    print(f"[PROCESS VIDEO JOB MODE] resolved_render_mode={render_mode}")
    print(f"[PROCESS VIDEO JOB CONFIG] resolved_dual_region_config={dual_region_config}")


    log = step_logger or (lambda _msg: None)

    source_video_path = original_video_path or video_path
    if not proxy_video_path:
        proxy_video_path = os.path.join(output_dir, "proxy.mp4")
        print(f"[PROXY GENERATION START] source={source_video_path} proxy={proxy_video_path}")
        subprocess.run(["ffmpeg", "-y", "-i", source_video_path, "-vf", "scale=960:-1", proxy_video_path], check=True)
        print(f"[PROXY GENERATION COMPLETE] proxy={proxy_video_path}")
    print(f"[AI USING PROXY VIDEO] {proxy_video_path}")

    log("[STEP 5 - TRANSCRIPTION START]")
    t_start = time.perf_counter()
    print(f"[WHISPER USING PROXY] {proxy_video_path}")
    transcription = transcribe_video(proxy_video_path)
    log(f"[STEP 6 - TRANSCRIPTION FINISH] elapsed={time.perf_counter() - t_start:.2f}s")

    log("[STEP 7 - CLIP DETECTION START]")
    d_start = time.perf_counter()
    hooks = detect_hooks(
        transcription,
        min_duration=min_clip_length,
        max_duration=max_clip_length,
        max_clips=max_clips,
        min_score=min_score,
        overlap_tolerance=overlap_tolerance,
    )
    log(f"[STEP 8 - CLIP DETECTION FINISH] elapsed={time.perf_counter() - d_start:.2f}s")
    broll_engine = BRollEngine()
    generated_clips = []
    timeline_broll = []
    timeline_cuts = []
    raw_clip_paths = []

    print(
        f"\nHOOKS RANKEADOS: total={len(hooks)} "
        f"min_clip_length={min_clip_length} max_clip_length={max_clip_length} "
        f"max_clips={max_clips} min_score={min_score} overlap_tolerance={overlap_tolerance}\n"
    )

    for index, hook in enumerate(hooks):

        print(hook)

        raw_clip_path = cut_clip(
            source_video_path,
            hook["start"],
            hook["end"],
            f"raw_clip_{index}.mp4",
            output_dir=output_dir,
        )

        raw_clip_paths.append(raw_clip_path)
        generated_clips.append({
            "raw_clip_path": raw_clip_path,
            "clip_path": raw_clip_path,
            "final_clip": raw_clip_path,
            "start": hook["start"],
            "end": hook["end"],
            "text": hook["text"],
            "viral_score": hook["viral_score"],
            "hook_score": hook.get("hook_score", hook["viral_score"]),
            "emotional_score": hook["emotional_score"],
            "retention_score": hook["retention_score"],
            "title_suggestion": "",
            "caption_suggestion": "",
            "description_suggestion": "",
            "hashtags": [],
            "emotion": "neutro",
            "category": "curiosidade",
            "viral_reason": "",
            "title_options": [],
            "broll_timeline": [],
        })
        timeline_cuts.append({
            "id": f"cut-{index}",
            "label": f"Cut {index + 1}",
            "start": hook["start"],
            "end": hook["start"] + 0.1,
        })

    should_wait_for_dual_region_setup = render_mode == "dual_region" and not dual_region_config
    if should_wait_for_dual_region_setup:
        analysis_id = os.path.basename(output_dir.rstrip("/"))
        print("[DUAL REGION EARLY RETURN]")
        print("[DUAL REGION WAIT STATE SAVED]")
        print("[DUAL REGION RENDER PIPELINE SKIPPED]")
        print("[DUAL REGION WAITING FOR SETUP]")
        print(f"[DUAL REGION ANALYSIS READY] analysis_id={analysis_id}")
        next_state = {
            "analysisId": analysis_id,
            "render_mode": "dual_region",
            "status": "waiting_dual_region",
            "dual_region_ready": False,
            "clips": generated_clips,
            "raw_clips": raw_clip_paths,
            "video_path": source_video_path,
            "hooks": [
                {
                    "id": f"hook-{index}",
                    "label": "Hook",
                    "start": hook["start"],
                    "end": hook["end"],
                    "text": hook["text"],
                }
                for index, hook in enumerate(generated_clips)
            ],
            "broll": [],
            "cuts": timeline_cuts,
        }
        set_timeline_state(next_state)
        save_timeline_state_for_analysis(analysis_id, next_state)
        return {
            "text": " ".join([segment["text"] for segment in transcription["segments"]]),
            "hooks": generated_clips,
            "status": "WAITING_FOR_DUAL_REGION_SETUP",
            "analysis_id": analysis_id,
            "render_mode": "dual_region",
            "raw_clips": raw_clip_paths,
            "timeline": {"broll": [], "cuts": timeline_cuts},
        }

    if should_wait_for_dual_region_setup:
        raise RuntimeError("dual-region render pipeline reached while waiting for setup")

    log("[STEP 9 - RENDER START]")
    r_start = time.perf_counter()

    for index, hook in enumerate(generated_clips):

        raw_clip_path = hook["raw_clip_path"]
        processed_clip_path = raw_clip_path
        if render_mode == "ai_tracking":
            print("[RENDER MODE OVERRIDE] entering_ai_tracking_branch")
            print(f"[TRACKING USING PROXY] {proxy_video_path}")
            print(f"[FINAL RENDER USING ORIGINAL SOURCE] {source_video_path}")
            print("[PROXY COORDINATES UPSCALED] via normalized tracking coordinates")
            processed_clip_path = render_vertical_clip(
                raw_clip_path,
                transcription["segments"],
                os.path.join(output_dir, f"clip_{index}.mp4"),
                speaker_segments=transcription.get("speaker_segments", []),
                tracking_video_path=proxy_video_path,
                original_video_path=source_video_path,
            )
        elif render_mode == "dual_region" and dual_region_config:
            print("[DUAL REGION RENDER START]")
            print(f"[DUAL REGION CONFIG LOAD] {dual_region_config}")
            processed_clip_path = os.path.join(output_dir, f"clip_{index}_dual.mp4")
            render_dual_region_clip(raw_clip_path, processed_clip_path, dual_region_config)
            print("[DUAL REGION RENDER COMPLETE]")
        elif render_mode == "semi_auto":
            processed_clip_path = os.path.join(output_dir, f"clip_{index}_semi_auto.mp4")
            render_semi_auto_vertical(raw_clip_path, processed_clip_path)
        elif render_mode == "raw_only":
            print("[RENDER MODE OVERRIDE] raw_only_no_vertical_render")
        elif render_mode == "dual_region" and not dual_region_config:
            raise RuntimeError("dual-region render called without dual_region_config")

        segment_timeline = broll_engine.build_timeline([
            segment for segment in transcription["segments"]
            if hook["start"] <= segment.get("start", 0) <= hook["end"]
        ])

        final_clip_path = apply_broll_overlay(
            processed_clip_path,
            segment_timeline,
            f"clip_{index}_final.mp4",
            output_dir=output_dir,
            quality_profile="export",
        )

        metadata = generate_social_metadata(hook.get("text", ""), hook.get("viral_score", 0))
        ai_metadata = generate_clip_metadata(hook.get("text", ""))

        hook.update({
            "clip_path": processed_clip_path,
            "final_clip": final_clip_path,
            "viral_score": ai_metadata.get("score", hook["viral_score"]),
            "title_suggestion": ai_metadata.get("titles", [metadata["title"]])[0],
            "caption_suggestion": ai_metadata.get("hook", metadata["caption"]),
            "description_suggestion": ai_metadata.get("description", metadata["description"]),
            "hashtags": metadata["hashtags"],
            "emotion": ai_metadata.get("emotion", "neutro"),
            "category": ai_metadata.get("category", "curiosidade"),
            "viral_reason": ai_metadata.get("viral_reason", ""),
            "title_options": ai_metadata.get("titles", []),
            "broll_timeline": segment_timeline,
        })

        for broll_index, broll_segment in enumerate(segment_timeline):
            timeline_broll.append({
                "id": f"br-{index}-{broll_index}",
                "label": broll_segment.get("asset", "B-roll"),
                "start": float(broll_segment.get("start", 0)),
                "end": float(broll_segment.get("end", broll_segment.get("start", 0) + 0.5)),
            })

    log(f"[STEP 10 - RENDER FINISH] elapsed={time.perf_counter() - r_start:.2f}s")

    full_text = " ".join(
        [segment["text"] for segment in transcription["segments"]]
    )

    return {
        "text": full_text,
        "hooks": generated_clips,
        "status": "completed",
        "timeline": {
            "broll": timeline_broll,
            "cuts": timeline_cuts,
        },
    }
