from app.services.youtube_service import FormatSelector


def test_format_selector_prioritizes_resolution_over_progressive_h264_360p():
    info = {
        "formats": [
            {"format_id": "18", "height": 360, "width": 640, "vcodec": "avc1.42001E", "acodec": "mp4a.40.2", "ext": "mp4", "tbr": 500},
            {"format_id": "248", "height": 1080, "width": 1920, "vcodec": "vp9", "acodec": "none", "ext": "webm", "tbr": 2500},
            {"format_id": "140", "vcodec": "none", "acodec": "mp4a.40.2", "ext": "m4a", "abr": 128},
        ]
    }

    selected = FormatSelector("1080p").select(info)

    assert selected.video_format_id == "248"
    assert selected.audio_format_id == "140"
    assert selected.download_format == "248+140"


def test_format_selector_prefers_h264_at_same_resolution():
    info = {
        "formats": [
            {"format_id": "248", "height": 1080, "width": 1920, "vcodec": "vp9", "acodec": "none", "ext": "webm", "tbr": 2500},
            {"format_id": "137", "height": 1080, "width": 1920, "vcodec": "avc1.640028", "acodec": "none", "ext": "mp4", "tbr": 2200},
            {"format_id": "140", "vcodec": "none", "acodec": "mp4a.40.2", "ext": "m4a", "abr": 128},
        ]
    }

    selected = FormatSelector("1080p").select(info)

    assert selected.video_format_id == "137"
    assert selected.audio_format_id == "140"
