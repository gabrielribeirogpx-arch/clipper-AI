import concurrent.futures
import logging
import os
from functools import lru_cache


logger = logging.getLogger(__name__)

CAPTION_PRE_ROLL_SECONDS = 0.25
TRANSCRIPTION_PROVIDER_FASTER_WHISPER = "faster_whisper"
TRANSCRIPTION_PROVIDER_WHISPERX = "whisperx"
DEFAULT_TRANSCRIPTION_PROVIDER = TRANSCRIPTION_PROVIDER_FASTER_WHISPER
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small").strip() or "small"
WHISPERX_TIMEOUT_SECONDS = int(os.getenv("WHISPERX_TIMEOUT_SECONDS", "7200"))
PYANNOTE_TIMEOUT_SECONDS = int(os.getenv("PYANNOTE_TIMEOUT_SECONDS", "7200"))
VALID_WHISPER_DEVICES = {"auto", "cpu", "cuda"}


def _is_cuda_available():
    try:
        import torch
    except ImportError:
        logger.warning("Torch is not installed. Falling back to CPU for WhisperX.")
        return False

    return torch.cuda.is_available()


def _requested_device():
    requested_device = os.getenv("WHISPER_DEVICE", "auto").strip().lower() or "auto"
    if requested_device not in VALID_WHISPER_DEVICES:
        logger.warning(
            "Invalid WHISPER_DEVICE=%r. Falling back to automatic device detection.",
            requested_device,
        )
        return "auto"
    return requested_device


def _resolve_device():
    requested_device = _requested_device()
    if requested_device == "auto":
        return "cuda" if _is_cuda_available() else "cpu"
    if requested_device == "cuda" and not _is_cuda_available():
        logger.warning(
            "WHISPER_DEVICE=cuda was requested, but Torch CUDA is not available. "
            "Falling back to CPU."
        )
        return "cpu"
    return requested_device


def _resolve_faster_whisper_device():
    requested_device = _requested_device()
    if requested_device == "auto":
        return "cuda" if _is_cuda_available() else "cpu"
    if requested_device == "cuda" and not _is_cuda_available():
        logger.warning(
            "WHISPER_DEVICE=cuda was requested, but CUDA is not available. "
            "Falling back to CPU."
        )
        return "cpu"
    return requested_device


def _is_cuda_runtime_error(exc):
    error_text = str(exc).lower()
    return any(
        marker in error_text
        for marker in ("cuda", "cudnn", "cublas", "ctranslate2", "dll")
    )


def _compute_type_for_device(device):
    return "float16" if device == "cuda" else "int8"


@lru_cache(maxsize=4)
def _load_faster_whisper_model(model_name, device):
    from faster_whisper import WhisperModel

    return WhisperModel(
        model_name,
        device=device,
        compute_type=_compute_type_for_device(device),
    )


@lru_cache(maxsize=4)
def _load_whisperx_model(model_name, device):
    import whisperx

    return whisperx.load_model(
        model_name,
        device,
        compute_type=_compute_type_for_device(device),
    )


def _normalize_segments(segments):
    normalized = []
    for segment in segments or []:
        start = float(segment.get("start", 0.0) or 0.0)
        end = float(segment.get("end", start) or start)
        normalized.append(
            {
                **segment,
                "start": max(0.0, start - CAPTION_PRE_ROLL_SECONDS),
                "end": max(max(0.0, start - CAPTION_PRE_ROLL_SECONDS) + 0.05, end),
                "text": str(segment.get("text", "") or ""),
            }
        )
    return normalized


def _result_with_text(result):
    segments = _normalize_segments(result.get("segments", []))
    return {**result, "segments": segments, "text": " ".join(s.get("text", "").strip() for s in segments).strip()}


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
    except Exception as exc:
        logger.warning("DIARIZATION_FAILED: %s", exc)
        aligned_result["speaker_segments"] = []
    finally:
        if profiler:
            profiler.end_timer("pyannote_diarization")
    return aligned_result


def _faster_whisper_result(segments):
    normalized = _result_with_text({"segments": segments})
    return {"text": normalized["text"], "segments": normalized["segments"]}


def _transcribe_with_faster_whisper_device(video_path, model_name, device, profiler=None):
    if profiler:
        profiler.start_timer("whisper_load_model")
    try:
        model = _load_faster_whisper_model(model_name, device)
    finally:
        if profiler:
            profiler.end_timer("whisper_load_model")

    if profiler:
        profiler.start_timer("whisper_transcription")
    try:
        segments_iter, _info = model.transcribe(video_path)
        segments = [
            {
                "start": float(segment.start or 0.0),
                "end": float(segment.end or 0.0),
                "text": str(segment.text or ""),
            }
            for segment in segments_iter
        ]
    finally:
        if profiler:
            profiler.end_timer("whisper_transcription")

    return _faster_whisper_result(segments)


def _transcribe_with_faster_whisper(video_path, profiler=None):
    device = _resolve_faster_whisper_device()
    model_name = WHISPER_MODEL
    logger.info(
        "TRANSCRIPTION_DEVICE_SELECTED provider=faster_whisper device=%s compute_type=%s",
        device,
        _compute_type_for_device(device),
    )

    try:
        return _transcribe_with_faster_whisper_device(video_path, model_name, device, profiler=profiler)
    except Exception as exc:
        if device != "cuda" or not _is_cuda_runtime_error(exc):
            raise

        logger.warning(
            "TRANSCRIPTION_GPU_FAILED_FALLBACK_CPU provider=faster_whisper error=%s",
            exc,
        )
        logger.info(
            "TRANSCRIPTION_CPU_FALLBACK_STARTED provider=faster_whisper device=cpu compute_type=int8"
        )
        result = _transcribe_with_faster_whisper_device(video_path, model_name, "cpu", profiler=profiler)
        logger.info("TRANSCRIPTION_CPU_FALLBACK_SUCCESS provider=faster_whisper")
        return result


def _transcribe_with_whisperx(video_path, diarize: bool = True, profiler=None):
    import whisperx

    device = _resolve_device()
    audio = whisperx.load_audio(video_path)
    model_name = WHISPER_MODEL

    if profiler:
        profiler.start_timer("whisper_load_model")
    model = _load_whisperx_model(model_name, device)
    if profiler:
        profiler.end_timer("whisper_load_model")
        profiler.start_timer("whisper_transcription")
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        result = executor.submit(model.transcribe, audio).result(timeout=WHISPERX_TIMEOUT_SECONDS)
    if profiler:
        profiler.end_timer("whisper_transcription")

    aligned_result = result
    try:
        if profiler:
            profiler.start_timer("whisper_alignment")
        model_a, metadata = whisperx.load_align_model(
            language_code=result["language"],
            device=device,
        )
        aligned_result = whisperx.align(
            result.get("segments", []),
            model_a,
            metadata,
            audio,
            device,
        )
    except Exception as exc:
        logger.warning("WHISPER_ALIGNMENT_FAILED: %s", exc)
        aligned_result = result
    finally:
        if profiler:
            profiler.end_timer("whisper_alignment")

    aligned_result = _result_with_text({**aligned_result, "provider": TRANSCRIPTION_PROVIDER_WHISPERX, "model": model_name})

    if diarize:
        aligned_result = _run_diarization(whisperx, audio, aligned_result, device, profiler=profiler)

    return aligned_result


def _selected_provider():
    provider = os.getenv("TRANSCRIPTION_PROVIDER", DEFAULT_TRANSCRIPTION_PROVIDER).strip().lower()
    if provider not in {TRANSCRIPTION_PROVIDER_FASTER_WHISPER, TRANSCRIPTION_PROVIDER_WHISPERX}:
        logger.warning(
            "Invalid TRANSCRIPTION_PROVIDER=%r. Falling back to %s.",
            provider,
            DEFAULT_TRANSCRIPTION_PROVIDER,
        )
        return DEFAULT_TRANSCRIPTION_PROVIDER
    return provider


def transcribe_video(video_path, diarize: bool = True, profiler=None):
    provider = _selected_provider()
    if provider == TRANSCRIPTION_PROVIDER_WHISPERX:
        try:
            return _transcribe_with_whisperx(video_path, diarize=diarize, profiler=profiler)
        except Exception as exc:
            logger.warning("TRANSCRIPTION_PROVIDER_FAILED provider=whisperx error=%s", exc)
            print(f"[TRANSCRIPTION_PROVIDER_FAILED] provider=whisperx error={exc}")

    return _transcribe_with_faster_whisper(video_path, profiler=profiler)
