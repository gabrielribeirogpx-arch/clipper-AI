from app.services.viral_detector import detect_and_rank_hooks


def detect_hooks(transcription):
    segments = transcription["segments"]
    return detect_and_rank_hooks(segments)
