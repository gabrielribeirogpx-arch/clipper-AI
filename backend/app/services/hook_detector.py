from app.services.viral_detector import detect_and_rank_hooks


def detect_hooks(
    transcription,
    min_duration: int = 30,
    max_duration: int = 90,
    max_clips: int = 25,
    min_score: float = 0.45,
    overlap_tolerance: float = 0.6,
):
    segments = transcription["segments"]
    return detect_and_rank_hooks(
        segments,
        min_duration=min_duration,
        max_duration=max_duration,
        max_clips=max_clips,
        min_score=min_score,
        overlap_tolerance=overlap_tolerance,
    )
