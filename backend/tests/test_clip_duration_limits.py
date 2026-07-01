from app.services.viral_detector import detect_and_rank_hooks


def test_viral_detector_never_exceeds_max_clip_length():
    segments = [
        {"start": i * 10.0, "end": i * 10.0 + 8.0, "text": "This is an exciting segment with useful context"}
        for i in range(30)
    ]

    clips = detect_and_rank_hooks(
        segments,
        min_duration=30,
        max_duration=90,
        max_clips=10,
        min_score=0.0,
        overlap_tolerance=1.0,
    )

    assert clips
    assert all((clip["end"] - clip["start"]) <= 90 for clip in clips)
