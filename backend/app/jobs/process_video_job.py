from app.services.whisper_service import transcribe_video
from app.services.hook_detector import detect_hooks
from app.services.ffmpeg_service import cut_clip
from app.services.tiktok_subtitle_service import create_tiktok_subtitles


def process_video(video_path):

    transcription = transcribe_video(video_path)

    hooks = detect_hooks(transcription)

    generated_clips = []

    print("\nHOOKS ENCONTRADOS:\n")

    for index, hook in enumerate(hooks):

        print(hook)

        raw_clip_path = cut_clip(
            video_path,
            hook["start"],
            hook["end"],
            f"raw_clip_{index}.mp4"
        )

        clip_path = create_tiktok_subtitles(
            raw_clip_path,
            transcription["segments"],
            f"app/clips/clip_{index}.mp4"
        )

        generated_clips.append({
            "clip": clip_path,
            "start": hook["start"],
            "end": hook["end"],
            "text": hook["text"]
        })

    full_text = " ".join(
        [segment["text"] for segment in transcription["segments"]]
    )

    return {
        "text": full_text,
        "hooks": generated_clips
    }