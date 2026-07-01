import importlib
import sys
import types


class ImportBlocker:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "whisperx" or fullname.startswith("pyannote"):
            raise AssertionError(f"blocked import attempted: {fullname}")
        return None


class FakeSegment:
    start = 1.0
    end = 2.0
    text = " hello"


class FakeInfo:
    language = "en"
    language_probability = 0.99


class FakeWhisperModel:
    def __init__(self, *args, **kwargs):
        pass

    def transcribe(self, video_path):
        return iter([FakeSegment()]), FakeInfo()


def test_faster_whisper_provider_does_not_import_whisperx_or_pyannote(monkeypatch):
    monkeypatch.setenv("TRANSCRIPTION_PROVIDER", "faster_whisper")
    monkeypatch.setenv("WHISPER_DEVICE", "cpu")

    fake_faster_whisper = types.ModuleType("faster_whisper")
    fake_faster_whisper.WhisperModel = FakeWhisperModel
    monkeypatch.setitem(sys.modules, "faster_whisper", fake_faster_whisper)
    monkeypatch.delitem(sys.modules, "whisperx", raising=False)
    for module_name in list(sys.modules):
        if module_name.startswith("pyannote"):
            monkeypatch.delitem(sys.modules, module_name, raising=False)

    blocker = ImportBlocker()
    sys.meta_path.insert(0, blocker)
    try:
        whisper_service = importlib.import_module("app.services.whisper_service")
        whisper_service._load_faster_whisper_model.cache_clear()
        result = whisper_service.transcribe_video("sample.mp4", diarize=True)
    finally:
        sys.meta_path.remove(blocker)

    assert "whisperx" not in sys.modules
    assert not any(module_name.startswith("pyannote") for module_name in sys.modules)
    assert set(result) == {"text", "segments"}
    assert result["text"] == "hello"
    assert result["segments"] == [{"start": 0.75, "end": 2.0, "text": " hello"}]


def test_faster_whisper_falls_back_to_cpu_on_cudnn_error(monkeypatch, caplog):
    monkeypatch.setenv("TRANSCRIPTION_PROVIDER", "faster_whisper")
    monkeypatch.setenv("WHISPER_DEVICE", "auto")

    fake_torch = types.ModuleType("torch")
    fake_torch.cuda = types.SimpleNamespace(is_available=lambda: True)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    model_calls = []

    class CudnnFallbackWhisperModel:
        def __init__(self, model_name, device, compute_type):
            model_calls.append(
                {"model_name": model_name, "device": device, "compute_type": compute_type}
            )
            if device == "cuda":
                raise RuntimeError(
                    "Could not locate cudnn_ops_infer64_8.dll. Please make sure it is in your library path!"
                )

        def transcribe(self, video_path):
            return iter([FakeSegment()]), FakeInfo()

    fake_faster_whisper = types.ModuleType("faster_whisper")
    fake_faster_whisper.WhisperModel = CudnnFallbackWhisperModel
    monkeypatch.setitem(sys.modules, "faster_whisper", fake_faster_whisper)

    whisper_service = importlib.import_module("app.services.whisper_service")
    whisper_service._load_faster_whisper_model.cache_clear()

    with caplog.at_level("INFO", logger="app.services.whisper_service"):
        result = whisper_service.transcribe_video("sample.mp4", diarize=True)

    assert model_calls == [
        {"model_name": "small", "device": "cuda", "compute_type": "float16"},
        {"model_name": "small", "device": "cpu", "compute_type": "int8"},
    ]
    assert set(result) == {"text", "segments"}
    assert result["text"] == "hello"
    assert result["segments"] == [{"start": 0.75, "end": 2.0, "text": " hello"}]
    assert "TRANSCRIPTION_DEVICE_SELECTED" in caplog.text
    assert "TRANSCRIPTION_GPU_FAILED_FALLBACK_CPU" in caplog.text
    assert "TRANSCRIPTION_CPU_FALLBACK_STARTED" in caplog.text
    assert "TRANSCRIPTION_CPU_FALLBACK_SUCCESS" in caplog.text
