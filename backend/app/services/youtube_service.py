import logging
import os
import shutil
import subprocess
import sys
import uuid

UPLOAD_DIR = "app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
logger = logging.getLogger(__name__)


def _format_download_section(start_time: str | None, end_time: str | None) -> str | None:
    if not start_time or not end_time:
        return None
    return f"*{start_time}-{end_time}"


def _resolve_ffmpeg_location() -> str | None:
    """Prefer ffmpeg binaries installed in the current Python environment."""
    env_bin_dir = os.path.dirname(sys.executable)
    candidates = [
        os.path.join(env_bin_dir, "ffmpeg.exe"),
        os.path.join(env_bin_dir, "ffmpeg"),
        os.path.join(env_bin_dir, "Scripts", "ffmpeg.exe"),
        os.path.join(env_bin_dir, "bin", "ffmpeg"),
    ]

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate

    return shutil.which("ffmpeg")


def download_youtube_video(youtube_url: str, start_time: str | None = None, end_time: str | None = None) -> str:
    output_template = os.path.join(UPLOAD_DIR, f"yt_{uuid.uuid4()}_%(id)s.%(ext)s")
    command = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--no-playlist",
        "-f",
        "mp4/bestvideo+bestaudio/best",
        "-o",
        output_template,
    ]

    ffmpeg_location = _resolve_ffmpeg_location()
    if ffmpeg_location:
        command.extend(["--ffmpeg-location", ffmpeg_location])

    section = _format_download_section(start_time, end_time)
    if section:
        command.extend(["--download-sections", section])

    command.append(youtube_url)
    logger.info("Executing yt-dlp command: %s", command)
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        logger.error("yt-dlp command failed: %s", command)
        logger.error("yt-dlp stdout: %s", error.stdout)
        logger.error("yt-dlp stderr: %s", error.stderr)
        raise

    logger.info("yt-dlp stdout: %s", result.stdout)
    logger.info("yt-dlp stderr: %s", result.stderr)

    matches = sorted([f for f in os.listdir(UPLOAD_DIR) if f.startswith("yt_")], key=lambda x: os.path.getmtime(os.path.join(UPLOAD_DIR, x)), reverse=True)
    if not matches:
        raise RuntimeError("Failed to download YouTube video")
    return os.path.join(UPLOAD_DIR, matches[0])
