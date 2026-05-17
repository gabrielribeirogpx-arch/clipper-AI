import logging
import os
import re

COOKIES_PATH = os.getenv(
    "YTDLP_COOKIES_PATH",
    "C:/temp/cookies.txt"
)

import shutil
import subprocess
import sys
import uuid
import tempfile
from dataclasses import dataclass

UPLOAD_DIR = "app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
logger = logging.getLogger(__name__)
PLAYER_CLIENT_CANDIDATES = ["web", "android", "tv", "ios"]

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


def _extract_max_height(formats_output: str) -> int:
    heights = [int(m.group(1)) for m in re.finditer(r"\b(\d{3,4})p\b", formats_output)]
    return max(heights) if heights else 0


def _list_formats_for_client(base_command: list[str], youtube_url: str, client: str) -> tuple[int, str]:
    format_command = [
        *base_command,
        "--extractor-args",
        f"youtube:player_client={client}",
        "-F",
        youtube_url,
    ]
    logger.info("[YOUTUBE AVAILABLE FORMATS] listing", extra={"client": client, "command": format_command})
    result = subprocess.run(format_command, check=False, capture_output=True, text=True)
    output = (result.stdout or "") + "\n" + (result.stderr or "")
    logger.info("[YOUTUBE AVAILABLE FORMATS]", extra={"client": client, "formats": output.strip(), "returncode": result.returncode})
    max_height = _extract_max_height(output) if result.returncode == 0 else 0
    return max_height, client


def download_youtube_video(youtube_url: str, start_time: str | None = None, end_time: str | None = None) -> str:
    output_template = os.path.join(UPLOAD_DIR, f"yt_{uuid.uuid4()}_%(id)s.%(ext)s")
    base_command = [
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
    ]

    command = [
        *base_command,
        "-f",
        "bv*+ba/b",
        "-S",
        "res:1080,fps",
        "--merge-output-format",
        "mp4",
        "--print",
        "before_dl:[YOUTUBE SELECTED FORMAT] id=%(format_id)s ext=%(ext)s note=%(format_note)s vcodec=%(vcodec)s acodec=%(acodec)s",
        "--print",
        "before_dl:[YOUTUBE VIDEO QUALITY] id=%(requested_formats.0.format_id)s res=%(requested_formats.0.resolution)s codec=%(requested_formats.0.vcodec)s fps=%(requested_formats.0.fps)s abr=%(requested_formats.0.tbr)s",
        "--print",
        "before_dl:[YOUTUBE AUDIO QUALITY] id=%(requested_formats.1.format_id)s abr=%(requested_formats.1.abr)s codec=%(requested_formats.1.acodec)s",
        "-o",
        output_template,
    ]

    cookies_file_path = os.path.abspath(COOKIES_PATH)
    temp_cookie_file = tempfile.NamedTemporaryFile(
        suffix=".txt",
        delete=False
    )

    shutil.copy2(cookies_file_path, temp_cookie_file.name)

    cookies_runtime_path = temp_cookie_file.name
    if os.path.isfile(cookies_file_path):
        base_command.extend(["--cookies", cookies_runtime_path])
        command.extend(["--cookies", cookies_runtime_path])
    else:
        logger.error("[YOUTUBE DOWNLOAD ERROR] cookies.txt não encontrado", extra={"cookies_file": cookies_file_path})
        raise YouTubeDownloadError(
            message="Arquivo de cookies não encontrado em C:/cookies.txt. Gere/atualize o arquivo e tente novamente.",
            category="missing_cookies",
        )

    ffmpeg_location = _resolve_ffmpeg_location()
    if ffmpeg_location:
        command.extend(["--ffmpeg-location", ffmpeg_location])
        base_command.extend(["--ffmpeg-location", ffmpeg_location])

    node_path = _resolve_node_path()
    if not node_path:
        logger.warning("Node.js não encontrado no PATH/venv; yt-dlp pode falhar em alguns vídeos.")

    section = _format_download_section(start_time, end_time)
    if section:
        command.extend(["--download-sections", section])

    client_results: list[tuple[int, str]] = []
    for client in PLAYER_CLIENT_CANDIDATES:
        max_height, checked_client = _list_formats_for_client(base_command, youtube_url, client)
        client_results.append((max_height, checked_client))

    best_height, best_client = max(client_results, key=lambda item: item[0])
    logger.info("[YOUTUBE CLIENT DECISION]", extra={"results": client_results, "selected_client": best_client, "selected_max_height": best_height})
    command.extend(["--extractor-args", f"youtube:player_client={best_client}"])

    command.append(youtube_url)
    logger.info("[YOUTUBE DOWNLOAD START] Iniciando download do YouTube", extra={"url": youtube_url})
    logger.info("[YT-DLP COMMAND]", extra={"command": command})
    try:
        result = subprocess.run(
            command, 
            check=False, 
            capture_output=True, 
            text=True
            
        )

        print("YT-DLP STDOUT:", result.stdout)
        print("YT-DLP STDERR:", result.stderr)
        print("YT-DLP RETURN CODE:", result.returncode)
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
    output_file = os.path.join(UPLOAD_DIR, matches[0])

    if ffmpeg_location:
        ffprobe_location = os.path.join(os.path.dirname(ffmpeg_location), "ffprobe")
        if os.name == "nt":
            ffprobe_location = f"{ffprobe_location}.exe"
        if not os.path.isfile(ffprobe_location):
            ffprobe_location = shutil.which("ffprobe")

        if ffprobe_location:
            probe_cmd = [
                ffprobe_location,
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type,width,height,codec_name,avg_frame_rate,bit_rate:format=bit_rate",
                "-of",
                "default=noprint_wrappers=1",
                output_file,
            ]
            probe_result = subprocess.run(probe_cmd, check=False, capture_output=True, text=True)
            if probe_result.returncode == 0:
                logger.info("[YOUTUBE SOURCE PROBE]", extra={"metadata": probe_result.stdout})
                final_width_match = re.search(r"width=(\d+)", probe_result.stdout)
                final_height_match = re.search(r"height=(\d+)", probe_result.stdout)
                final_bitrate_match = re.search(r"^bit_rate=(\d+)$", probe_result.stdout, re.MULTILINE)
                if final_width_match and final_height_match:
                    logger.info("[YOUTUBE FINAL RESOLUTION]", extra={"resolution": f"{final_width_match.group(1)}x{final_height_match.group(1)}"})
                if final_bitrate_match:
                    logger.info("[YOUTUBE FINAL_BITRATE]", extra={"bitrate": final_bitrate_match.group(1)})
            else:
                logger.warning("[YOUTUBE SOURCE PROBE FAILED]", extra={"stderr": probe_result.stderr})

    return output_file
