from app.services.viral_detector import detect_and_rank_hooks


def detect_hooks(transcription, min_duration: int = 30, max_duration: int = 90):
    segments = transcription["segments"]
    return detect_and_rank_hooks(segments, min_duration=min_duration, max_duration=max_duration)
