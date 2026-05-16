from app.services.whisper_service import transcribe_video
from app.services.hook_detector import detect_hooks
from app.services.ffmpeg_service import cut_clip, apply_broll_overlay
from app.services.vertical_render_service import render_vertical_clip
from app.services.broll_engine import BRollEngine
from app.services.social_metadata_service import generate_social_metadata


def process_video(
    video_path,
    min_clip_length: int = 30,
    max_clip_length: int = 90,
    max_clips: int = 25,
    min_score: float = 0.45,
    overlap_tolerance: float = 0.6,
):

    transcription = transcribe_video(video_path)

    hooks = detect_hooks(
        transcription,
        min_duration=min_clip_length,
        max_duration=max_clip_length,
        max_clips=max_clips,
        min_score=min_score,
        overlap_tolerance=overlap_tolerance,
    )
    broll_engine = BRollEngine()

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
            f"raw_clip_{index}.mp4"
        )

        processed_clip_path = render_vertical_clip(
            raw_clip_path,
            transcription["segments"],
            f"app/clips/clip_{index}.mp4",
            speaker_segments=transcription.get("speaker_segments", []),
        )

        segment_timeline = broll_engine.build_timeline([
            segment for segment in transcription["segments"]
            if hook["start"] <= segment.get("start", 0) <= hook["end"]
        ])

        preview_clip_path = apply_broll_overlay(
            processed_clip_path,
            segment_timeline,
            f"clip_{index}_preview.mp4"
        )

        export_clip_path = apply_broll_overlay(
            processed_clip_path,
            segment_timeline,
            f"clip_{index}_export.mp4"
        )


        metadata = generate_social_metadata(hook.get("text", ""), hook.get("viral_score", 0))

        generated_clips.append({
            "clip_path": processed_clip_path,
            "preview_clip": preview_clip_path,
            "export_clip": export_clip_path,
            "start": hook["start"],
            "end": hook["end"],
            "text": hook["text"],
            "viral_score": hook["viral_score"],
            "hook_score": hook.get("hook_score", hook["viral_score"]),
            "emotional_score": hook["emotional_score"],
            "retention_score": hook["retention_score"],
            "title_suggestion": metadata["title"],
            "caption_suggestion": metadata["caption"],
            "description_suggestion": metadata["description"],
            "hashtags": metadata["hashtags"],
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
