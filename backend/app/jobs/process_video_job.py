import os
import time

from app.services.whisper_service import transcribe_video
from app.services.hook_detector import detect_hooks
from app.services.ffmpeg_service import cut_clip, apply_broll_overlay
from app.services.vertical_render_service import render_vertical_clip, render_dual_region_clip
from app.services.broll_engine import BRollEngine
from app.services.social_metadata_service import generate_social_metadata
from app.services.ai_local_service import generate_clip_metadata


def process_video(
    video_path,
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


    log = step_logger or (lambda _msg: None)

    log("[STEP 5 - TRANSCRIPTION START]")
    t_start = time.perf_counter()
    transcription = transcribe_video(video_path)
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

    log("[STEP 9 - RENDER START]")
    r_start = time.perf_counter()

    generated_clips = []
    timeline_broll = []
    timeline_cuts = []

    print(
        f"\nHOOKS RANKEADOS: total={len(hooks)} "
        f"min_clip_length={min_clip_length} max_clip_length={max_clip_length} "
        f"max_clips={max_clips} min_score={min_score} overlap_tolerance={overlap_tolerance}\n"
    )

    for index, hook in enumerate(hooks):

        print(hook)

        raw_clip_path = cut_clip(
            video_path,
            hook["start"],
            hook["end"],
            f"raw_clip_{index}.mp4",
            output_dir=output_dir,
        )

        processed_clip_path = raw_clip_path
        if render_mode == "ai_tracking":
            processed_clip_path = render_vertical_clip(
                raw_clip_path,
                transcription["segments"],
                os.path.join(output_dir, f"clip_{index}.mp4"),
                speaker_segments=transcription.get("speaker_segments", []),
            )

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

        if render_mode == "dual_region" and dual_region_config:
            print("[DUAL REGION FINAL RENDER START]")
            render_dual_region_clip(raw_clip_path, final_clip_path, dual_region_config)
            print("[DUAL REGION FINAL RENDER SUCCESS]")


        metadata = generate_social_metadata(hook.get("text", ""), hook.get("viral_score", 0))
        ai_metadata = generate_clip_metadata(hook.get("text", ""))

        generated_clips.append({
            "raw_clip_path": raw_clip_path,
            "clip_path": processed_clip_path,
            "final_clip": final_clip_path,
            "start": hook["start"],
            "end": hook["end"],
            "text": hook["text"],
            "viral_score": ai_metadata.get("score", hook["viral_score"]),
            "hook_score": hook.get("hook_score", hook["viral_score"]),
            "emotional_score": hook["emotional_score"],
            "retention_score": hook["retention_score"],
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

        timeline_cuts.append({
            "id": f"cut-{index}",
            "label": f"Cut {index + 1}",
            "start": hook["start"],
            "end": hook["start"] + 0.1,
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
        "timeline": {
            "broll": timeline_broll,
            "cuts": timeline_cuts,
        },
    }
