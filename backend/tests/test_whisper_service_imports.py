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
