import whisperx


device = "cpu"
CAPTION_PRE_ROLL_SECONDS = 0.25

model = whisperx.load_model(
    "base",
    device,
    compute_type="int8"
)


def transcribe_video(video_path):

    audio = whisperx.load_audio(video_path)

    result = model.transcribe(
        audio,
        vad_filter=False,
        condition_on_previous_text=False,
    )

    model_a, metadata = whisperx.load_align_model(
        language_code=result["language"],
        device=device
    )

    aligned_result = whisperx.align(
        result["segments"],
        model_a,
        metadata,
        audio,
        device
    )

    for segment in aligned_result.get("segments", []):
        start = float(segment.get("start", 0.0) or 0.0)
        end = float(segment.get("end", start) or start)
        segment["start"] = max(0.0, start - CAPTION_PRE_ROLL_SECONDS)
        segment["end"] = max(segment["start"] + 0.05, end)

    return aligned_result
