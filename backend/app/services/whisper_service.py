import whisperx


device = "cpu"

model = whisperx.load_model(
    "base",
    device,
    compute_type="int8"
)


def transcribe_video(video_path):

    audio = whisperx.load_audio(video_path)

    result = model.transcribe(audio)

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

    return aligned_result