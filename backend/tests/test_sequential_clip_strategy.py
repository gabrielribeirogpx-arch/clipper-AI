import sys
import types

sys.modules.setdefault("cv2", types.SimpleNamespace())
sys.modules.setdefault("numpy", types.SimpleNamespace())
moviepy = types.ModuleType("moviepy")
editor = types.ModuleType("moviepy.editor")
editor.VideoFileClip = object
sys.modules.setdefault("moviepy", moviepy)
sys.modules.setdefault("moviepy.editor", editor)

from app.services.sequential_clip_service import _build_sequential_hooks


def transcription(duration: float):
    return {"segments": [{"start": i, "end": min(i + 10, duration), "text": f"Configurar projeto parte {i}."} for i in range(0, int(duration), 10)]}


def assert_contiguous(hooks, start, end):
    assert hooks[0]["start"] == start
    assert hooks[-1]["end"] == end
    seen = set()
    for idx, hook in enumerate(hooks):
        assert hook["start"] < hook["end"]
        assert (hook["start"], hook["end"]) not in seen
        seen.add((hook["start"], hook["end"]))
        if idx:
            assert hook["start"] == hooks[idx - 1]["end"]


def test_997_seconds_generates_17_ranges_without_gaps():
    hooks = _build_sequential_hooks(transcription(997), 0, 997, 60, False, False, True)
    assert len(hooks) == 17
    assert_contiguous(hooks, 0, 997)


def test_10_minutes_generates_exactly_10_clips():
    hooks = _build_sequential_hooks(transcription(600), 0, 600, 60, False, False, True)
    assert len(hooks) == 10
    assert_contiguous(hooks, 0, 600)


def test_selected_interval_only():
    hooks = _build_sequential_hooks(transcription(600), 120, 420, 60, False, False, True)
    assert len(hooks) == 5
    assert_contiguous(hooks, 120, 420)


def test_titles_and_filenames_are_distinct_and_valid():
    hooks = _build_sequential_hooks({"segments": [
        {"start": 0, "end": 60, "text": "Como configurar projeto agora."},
        {"start": 60, "end": 120, "text": "Erros reduzem qualidade exportacao."},
    ]}, 0, 120, 60, False, False, True)
    filenames = [h["filename"] for h in hooks]
    assert len(set(h["title"] for h in hooks)) == 2
    assert len(set(filenames)) == 2
    assert all(name.endswith(".mp4") and not any(ch in name for ch in '<>:"/\\|?*') for name in filenames)
