import os
import concurrent.futures

import whisperx


device = "cuda"
CAPTION_PRE_ROLL_SECONDS = 0.25
WHISPERX_TIMEOUT_SECONDS = int(os.getenv("WHISPERX_TIMEOUT_SECONDS", "1800"))
PYANNOTE_TIMEOUT_SECONDS = int(os.getenv("PYANNOTE_TIMEOUT_SECONDS", "900"))

model = whisperx.load_model(
    "base",
    device,
    compute_type="float16"
)


def _run_diarization(audio, aligned_result):
    try:
        diarize_model = whisperx.DiarizationPipeline(use_auth_token=None, device=device)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            diarization = executor.submit(diarize_model, audio).result(timeout=PYANNOTE_TIMEOUT_SECONDS)
        aligned_result["speaker_segments"] = [
            {
                "speaker": str(item.get("speaker", "SPEAKER_00")),
                "start": float(item.get("start", 0.0) or 0.0),
                "end": float(item.get("end", 0.0) or 0.0),
            }
            for item in diarization.to_dict("records")
        ]
    except concurrent.futures.TimeoutError:
        print(f"[PYANNOTE TIMEOUT] timeout={PYANNOTE_TIMEOUT_SECONDS}s")
        aligned_result["speaker_segments"] = []
    except Exception:
        aligned_result["speaker_segments"] = []
    return aligned_result


def transcribe_video(video_path, diarize: bool = True):
    audio = whisperx.load_audio(video_path)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        result = executor.submit(model.transcribe, audio).result(timeout=WHISPERX_TIMEOUT_SECONDS)

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

    if diarize:
        aligned_result = _run_diarization(audio, aligned_result)

    return aligned_result
