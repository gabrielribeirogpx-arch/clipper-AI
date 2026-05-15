from app.services.whisper_service import transcribe_video
from app.services.hook_detector import detect_hooks
from app.services.ffmpeg_service import cut_clip, apply_broll_overlay
from app.services.tiktok_subtitle_service import create_tiktok_subtitles
from app.services.broll_engine import BRollEngine


def process_video(video_path):

    transcription = transcribe_video(video_path)

    hooks = detect_hooks(transcription)
    broll_engine = BRollEngine()

    generated_clips = []
    timeline_subtitles = []
    timeline_broll = []
    timeline_cuts = []

    print("\nHOOKS RANKEADOS:\n")

    for index, hook in enumerate(hooks):

        print(hook)

        raw_clip_path = cut_clip(
            video_path,
            hook["start"],
            hook["end"],
            f"raw_clip_{index}.mp4"
        )

        subtitled_clip_path = create_tiktok_subtitles(
            raw_clip_path,
            transcription["segments"],
            f"app/clips/clip_{index}.mp4"
        )

        segment_timeline = broll_engine.build_timeline([
            segment for segment in transcription["segments"]
            if hook["start"] <= segment.get("start", 0) <= hook["end"]
        ])

        clip_path = apply_broll_overlay(
            subtitled_clip_path,
            segment_timeline,
            f"clip_{index}_broll.mp4"
        )

        hook_subtitles = [
            segment for segment in transcription["segments"]
            if hook["start"] <= segment.get("start", 0) <= hook["end"]
        ]

        generated_clips.append({
            "clip": clip_path,
            "start": hook["start"],
            "end": hook["end"],
            "text": hook["text"],
            "viral_score": hook["viral_score"],
            "emotional_score": hook["emotional_score"],
            "retention_score": hook["retention_score"],
            "broll_timeline": segment_timeline,
        })

        timeline_cuts.append({
            "id": f"cut-{index}",
            "label": f"Cut {index + 1}",
            "start": hook["start"],
            "end": hook["start"] + 0.1,
        })

        for subtitle_index, segment in enumerate(hook_subtitles):
            timeline_subtitles.append({
                "id": f"sub-{index}-{subtitle_index}",
                "label": "Subtitle",
                "start": float(segment.get("start", 0)),
                "end": float(segment.get("end", segment.get("start", 0) + 0.5)),
                "text": segment.get("text", "").strip(),
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
            "subtitles": timeline_subtitles,
            "broll": timeline_broll,
            "cuts": timeline_cuts,
        },
    }
