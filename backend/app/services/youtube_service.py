import logging
import os
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass

UPLOAD_DIR = "app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
logger = logging.getLogger(__name__)
COOKIES_FILE = "backend/cookies.txt"

@dataclass
class YouTubeDownloadError(Exception):
    message: str
    category: str = "unknown"


def _resolve_node_path() -> str | None:
    """Resolve Node.js executable for yt-dlp JavaScript execution support."""
    env_bin_dir = os.path.dirname(sys.executable)
    candidates = [
        os.path.join(env_bin_dir, "node.exe"),
        os.path.join(env_bin_dir, "node"),
        os.path.join(env_bin_dir, "Scripts", "node.exe"),
        os.path.join(env_bin_dir, "bin", "node"),
    ]

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate

    return shutil.which("node")


def _classify_ytdlp_error(stderr: str, stdout: str) -> tuple[str, str]:
    output = f"{stderr}\n{stdout}".lower()

    if "sign in to confirm your age" in output or "age-restricted" in output:
        return (
            "age_restricted",
            "YouTube video is age-restricted and requires browser authentication.",
        )

    if "sign in to confirm you're not a bot" in output or "not a bot" in output:
        return ("anti_bot", "YouTube anti-bot protection triggered.")

    if "no supported javascript runtime could be found" in output:
        return (
            "javascript_runtime",
            "YouTube extraction requires a JavaScript runtime. Install Node.js and retry.",
        )

    if "video unavailable" in output:
        return ("unavailable", "YouTube video is unavailable or inaccessible.")

    return ("unknown", "Failed to ingest YouTube video. Please verify URL and access permissions.")



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
        "--no-warnings",
        "--retries",
        "5",
        "--fragment-retries",
        "10",
        "--concurrent-fragments",
        "4",
        "--js-runtimes",
        "node",
        "--remote-components",
        "ejs:github",
        "--extractor-args",
        "youtube:player_client=web",
        "-f",
        "mp4/bestvideo+bestaudio/best",
        "-o",
        output_template,
    ]

    cookies_file_path = os.path.abspath(COOKIES_FILE)
    if os.path.isfile(cookies_file_path):
        command.extend(["--cookies", cookies_file_path])
    else:
        logger.error("[YOUTUBE DOWNLOAD ERROR] cookies.txt não encontrado", extra={"cookies_file": cookies_file_path})
        raise YouTubeDownloadError(
            message="Arquivo de cookies não encontrado em backend/cookies.txt. Gere/atualize o arquivo e tente novamente.",
            category="missing_cookies",
        )

    ffmpeg_location = _resolve_ffmpeg_location()
    if ffmpeg_location:
        command.extend(["--ffmpeg-location", ffmpeg_location])

    node_path = _resolve_node_path()
    if not node_path:
        logger.warning("Node.js não encontrado no PATH/venv; yt-dlp pode falhar em alguns vídeos.")

    section = _format_download_section(start_time, end_time)
    if section:
        command.extend(["--download-sections", section])

    command.append(youtube_url)
    logger.info("[YOUTUBE DOWNLOAD START] Iniciando download do YouTube", extra={"url": youtube_url})
    logger.info("[YT-DLP COMMAND]", extra={"command": command})
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        logger.exception("yt-dlp execution crashed", extra={"command": command})
        raise YouTubeDownloadError(
            message=f"Failed to execute yt-dlp: {exc}",
            category="execution_error",
        ) from exc
    logger.info("[YT-DLP STDOUT]", extra={"stdout": result.stdout})
    logger.info("[YT-DLP STDERR]", extra={"stderr": result.stderr})

    if result.returncode != 0:
        category, message = _classify_ytdlp_error(result.stderr or "", result.stdout or "")
        raw_error = (result.stderr or result.stdout or message or "yt-dlp command failed").strip()
        logger.error(
            "[YOUTUBE DOWNLOAD ERROR] yt-dlp command failed",
            extra={
                "command": command,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "error_category": category,
            },
        )
        raise YouTubeDownloadError(message=raw_error, category=category)

    logger.info(
        "[YOUTUBE DOWNLOAD SUCCESS] yt-dlp command finished",
        extra={
            "command": command,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "error_category": "none",
        },
    )

    matches = sorted([f for f in os.listdir(UPLOAD_DIR) if f.startswith("yt_")], key=lambda x: os.path.getmtime(os.path.join(UPLOAD_DIR, x)), reverse=True)
    if not matches:
        logger.error("yt-dlp reported success but no output file was found", extra={"upload_dir": UPLOAD_DIR})
        raise YouTubeDownloadError(
            message="Failed to locate downloaded YouTube video file.",
            category="missing_output",
        )
    return os.path.join(UPLOAD_DIR, matches[0])
