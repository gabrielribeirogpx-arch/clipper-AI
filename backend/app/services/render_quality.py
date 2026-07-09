EXPORT_QUALITY_MODE = __import__("os").getenv("EXPORT_QUALITY_MODE", "original").strip().lower()
if EXPORT_QUALITY_MODE not in {"original", "high", "balanced"}:
    print(f"[EXPORT QUALITY] invalid_mode={EXPORT_QUALITY_MODE} fallback=original")
    EXPORT_QUALITY_MODE = "original"

EXPORT_CRF = 18 if EXPORT_QUALITY_MODE == "balanced" else 14
EXPORT_PRESET = "medium" if EXPORT_QUALITY_MODE == "balanced" else "slow"
EXPORT_AUDIO_BITRATE = "320k"

EXPORT_VIDEO_CODEC = "libx264"
EXPORT_AUDIO_CODEC = "aac"
EXPORT_PIXEL_FORMAT = "yuv420p"
EXPORT_MOVFLAGS = "+faststart"
VERTICAL_PREMIUM_FILTER = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
