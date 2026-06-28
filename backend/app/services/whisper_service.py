import concurrent.futures
import logging
import os
from functools import lru_cache


logger = logging.getLogger(__name__)

CAPTION_PRE_ROLL_SECONDS = 0.25
WHISPERX_TIMEOUT_SECONDS = int(os.getenv("WHISPERX_TIMEOUT_SECONDS", "7200"))
PYANNOTE_TIMEOUT_SECONDS = int(os.getenv("PYANNOTE_TIMEOUT_SECONDS", "7200"))
VALID_WHISPER_DEVICES = {"cpu", "cuda"}


def _is_cuda_available():
    try:
        import torch
    except ImportError:
        logger.warning("Torch is not installed. Falling back to CPU for WhisperX.")
        return False

    return torch.cuda.is_available()


def _resolve_device():
    requested_device = os.getenv("WHISPER_DEVICE", "").strip().lower()
    cuda_available = _is_cuda_available()

    if requested_device:
        if requested_device not in VALID_WHISPER_DEVICES:
            logger.warning(
                "Invalid WHISPER_DEVICE=%r. Falling back to automatic device detection.",
                requested_device,
            )
        elif requested_device == "cuda" and not cuda_available:
            logger.warning(
                "WHISPER_DEVICE=cuda was requested, but Torch CUDA is not available. "
                "Falling back to CPU."
            )
            return "cpu"
        else:
            return requested_device

    return "cuda" if cuda_available else "cpu"


def _compute_type_for_device(device):
    return "float16" if device == "cuda" else "int8"


@lru_cache(maxsize=2)
def _load_whisper_model(device):
    import whisperx

    return whisperx.load_model(
        "base",
        device,
        compute_type=_compute_type_for_device(device),
    )


def _run_diarization(whisperx, audio, aligned_result, device, profiler=None):
    try:
        if profiler:
            profiler.start_timer("pyannote_diarization")
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
    finally:
        if profiler:
            profiler.end_timer("pyannote_diarization")
    return aligned_result


def transcribe_video(video_path, diarize: bool = True, profiler=None):
    import whisperx

    device = _resolve_device()
    audio = whisperx.load_audio(video_path)

    if profiler:
        profiler.start_timer("whisper_load_model")
    model = _load_whisper_model(device)
    if profiler:
        profiler.end_timer("whisper_load_model")
        profiler.start_timer("whisper_transcription")
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        result = executor.submit(model.transcribe, audio).result(timeout=WHISPERX_TIMEOUT_SECONDS)
    if profiler:
        profiler.end_timer("whisper_transcription")

    if profiler:
        profiler.start_timer("whisper_alignment")
    model_a, metadata = whisperx.load_align_model(
        language_code=result["language"],
        device=device,
    )

    aligned_result = whisperx.align(
        result["segments"],
        model_a,
        metadata,
        audio,
        device,
    )
    if profiler:
        profiler.end_timer("whisper_alignment")

    for segment in aligned_result.get("segments", []):
        start = float(segment.get("start", 0.0) or 0.0)
        end = float(segment.get("end", start) or start)
        segment["start"] = max(0.0, start - CAPTION_PRE_ROLL_SECONDS)
        segment["end"] = max(segment["start"] + 0.05, end)

    if diarize:
        aligned_result = _run_diarization(whisperx, audio, aligned_result, device, profiler=profiler)

    return aligned_result
