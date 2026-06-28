import logging
import os
import re
import time

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
QUALITY_HEIGHTS = {
    "720p": 720,
    "1080p": 1080,
    "4k": 2160,
}

YT_DLP_TIMEOUT_SECONDS = int(os.getenv("YT_DLP_TIMEOUT_SECONDS", "7200"))

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




def _build_format_attempts(video_quality: str) -> list[dict[str, str]]:
    normalized_quality = (video_quality or "1080p").strip().lower()
    max_height = QUALITY_HEIGHTS.get(normalized_quality, QUALITY_HEIGHTS["1080p"])
    return [
        {
            "name": "h264_avc_requested_quality",
            "selector": f"bestvideo[vcodec*=avc1][height<={max_height}]+bestaudio/best[vcodec*=avc1][height<={max_height}]/best[ext=mp4][height<={max_height}]",
        },
        {
            "name": "bestvideo_requested_quality",
            "selector": f"bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]",
        },
        {
            "name": "best_video_audio_any_quality",
            "selector": "bv*+ba/best",
        },
        {
            "name": "best_single_file",
            "selector": "best",
        },
    ]


def _has_invalid_cookies_warning(stderr: str, stdout: str) -> bool:
    output = f"{stderr}\n{stdout}".lower()
    cookie_markers = (
        "cookie",
        "cookies",
    )
    invalid_markers = (
        "invalid",
        "expired",
        "malformed",
        "could not copy chrome cookie database",
        "failed to decrypt",
        "unable to open database file",
        "does not look like a netscape format cookies file",
    )
    return any(marker in output for marker in cookie_markers) and any(marker in output for marker in invalid_markers)


def _build_download_command(
    base_command: list[str],
    format_selector: str,
    output_template: str,
    youtube_url: str,
    ffmpeg_location: str | None,
    section: str | None,
    cookies_runtime_path: str | None,
) -> list[str]:
    command = [
        *base_command,
        "--verbose",
        "-f",
        format_selector,
        "-S",
        "fps",
        "--merge-output-format",
        "mp4",
        "--print",
        "before_dl:[YOUTUBE SELECTED FORMAT] id=%(format_id)s ext=%(ext)s note=%(format_note)s vcodec=%(vcodec)s acodec=%(acodec)s",
        "--print",
        "before_dl:[REAL FINAL FORMAT] %(format_id)s",
        "--print",
        "before_dl:[REAL FINAL RESOLUTION] %(resolution)s",
        "--print",
        "before_dl:[REAL FINAL VCODEC] %(vcodec)s",
        "--print",
        "before_dl:[REAL FINAL ACODEC] %(acodec)s",
        "--print",
        "before_dl:[FINAL DOWNLOAD FORMAT] id=%(format_id)s res=%(resolution)s tbr=%(tbr)s",
        "--print",
        "before_dl:[YOUTUBE VIDEO QUALITY] id=%(requested_formats.0.format_id)s res=%(requested_formats.0.resolution)s codec=%(requested_formats.0.vcodec)s fps=%(requested_formats.0.fps)s abr=%(requested_formats.0.tbr)s",
        "--print",
        "before_dl:[YOUTUBE AUDIO QUALITY] id=%(requested_formats.1.format_id)s abr=%(requested_formats.1.abr)s codec=%(requested_formats.1.acodec)s",
        "-o",
        output_template,
    ]
    if cookies_runtime_path:
        command.extend(["--cookies", cookies_runtime_path])
    if ffmpeg_location:
        command.extend(["--ffmpeg-location", ffmpeg_location])
    if section:
        command.extend(["--download-sections", section])
    command.append(youtube_url)
    return command


def _normalize_to_h264_mp4(media_path: str, ffmpeg_location: str | None) -> str:
    if not ffmpeg_location:
        return media_path

    ffprobe_location = os.path.join(os.path.dirname(ffmpeg_location), "ffprobe")
    if os.name == "nt":
        ffprobe_location = f"{ffprobe_location}.exe"
    if not os.path.isfile(ffprobe_location):
        ffprobe_location = shutil.which("ffprobe")
    if not ffprobe_location:
        return media_path

    probe_cmd = [
        ffprobe_location,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name:format=format_name",
        "-of",
        "default=noprint_wrappers=1",
        media_path,
    ]
    probe_result = subprocess.run(probe_cmd, check=False, capture_output=True, text=True)
    if probe_result.returncode != 0:
        logger.warning("[YOUTUBE NORMALIZE PROBE FAILED]", extra={"stderr": probe_result.stderr})
        return media_path

    probe_output = probe_result.stdout or ""
    codec_match = re.search(r"^codec_name=(.+)$", probe_output, re.MULTILINE)
    format_match = re.search(r"^format_name=(.+)$", probe_output, re.MULTILINE)
    codec_name = (codec_match.group(1).strip().lower() if codec_match else "")
    format_name = (format_match.group(1).strip().lower() if format_match else "")
    if codec_name == "h264" and "mp4" in format_name and media_path.lower().endswith(".mp4"):
        logger.info("[YOUTUBE NORMALIZE SKIPPED]", extra={"codec": codec_name, "format": format_name})
        return media_path

    root, _ext = os.path.splitext(media_path)
    normalized_path = f"{root}_h264.mp4"
    nvenc_cmd = [
        ffmpeg_location,
        "-y",
        "-i",
        media_path,
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-c:v",
        "h264_nvenc",
        "-preset",
        "p4",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        normalized_path,
    ]
    logger.info("[YOUTUBE NORMALIZE START]", extra={"codec": codec_name, "format": format_name, "command": nvenc_cmd})
    normalize_result = subprocess.run(nvenc_cmd, check=False, capture_output=True, text=True)
    if normalize_result.returncode != 0:
        libx264_cmd = [*nvenc_cmd]
        libx264_cmd[libx264_cmd.index("h264_nvenc")] = "libx264"
        libx264_cmd[libx264_cmd.index("p4")] = "veryfast"
        logger.warning("[YOUTUBE NORMALIZE NVENC FALLBACK]", extra={"stderr": normalize_result.stderr, "command": libx264_cmd})
        normalize_result = subprocess.run(libx264_cmd, check=False, capture_output=True, text=True)
    if normalize_result.returncode != 0:
        logger.error("[YOUTUBE NORMALIZE FAILED]", extra={"stderr": normalize_result.stderr})
        return media_path
    logger.info("[YOUTUBE NORMALIZE SUCCESS]", extra={"output_file": normalized_path})
    return normalized_path

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



def download_youtube_video(youtube_url: str, start_time: str | None = None, end_time: str | None = None, video_quality: str = "1080p") -> str:
    perf_start = time.perf_counter()
    output_prefix = f"yt_{uuid.uuid4()}_"
    output_template = os.path.join(UPLOAD_DIR, f"{output_prefix}%(id)s.%(ext)s")
    base_command = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--no-playlist",
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

    normalized_quality = (video_quality or "1080p").strip().lower()
    format_attempts = _build_format_attempts(normalized_quality)
    print("[H264 SOURCE PREFERRED]")
    print(f"[DOWNLOAD QUALITY SELECTED] {normalized_quality}")

    cookies_file_path = os.path.abspath(COOKIES_PATH)
    temp_cookie_file = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
    temp_cookie_file.close()
    cookies_runtime_path = None
    try:
        if os.path.isfile(cookies_file_path):
            shutil.copy2(cookies_file_path, temp_cookie_file.name)
            cookies_runtime_path = temp_cookie_file.name
        else:
            logger.warning("[YTDLP_COOKIES_INVALID_WARNING] cookies.txt não encontrado; continuando sem cookies", extra={"cookies_file": cookies_file_path})

        ffmpeg_location = _resolve_ffmpeg_location()
        node_path = _resolve_node_path()
        if not node_path:
            logger.warning("Node.js não encontrado no PATH/venv; yt-dlp pode falhar em alguns vídeos.")

        section = _format_download_section(start_time, end_time)
        logger.info("[YOUTUBE DOWNLOAD START] Iniciando download do YouTube", extra={"url": youtube_url})

        last_result: subprocess.CompletedProcess[str] | None = None
        last_command: list[str] | None = None
        cookies_disabled = False

        for attempt_index, attempt in enumerate(format_attempts, start=1):
            active_cookies = None if cookies_disabled else cookies_runtime_path
            command = _build_download_command(
                base_command=base_command,
                format_selector=attempt["selector"],
                output_template=output_template,
                youtube_url=youtube_url,
                ffmpeg_location=ffmpeg_location,
                section=section,
                cookies_runtime_path=active_cookies,
            )
            logger.info(
                "[YTDLP_FORMAT_ATTEMPT]",
                extra={
                    "attempt": attempt_index,
                    "attempt_name": attempt["name"],
                    "format_selector": attempt["selector"],
                    "using_cookies": bool(active_cookies),
                },
            )
            logger.info("[REAL YT-DLP COMMAND]", extra={"purpose": "download", "command": command})
            try:
                result = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=YT_DLP_TIMEOUT_SECONDS,
                )
            except subprocess.TimeoutExpired as exc:
                logger.error("[YOUTUBE DOWNLOAD TIMEOUT]", extra={"timeout_seconds": YT_DLP_TIMEOUT_SECONDS})
                raise YouTubeDownloadError(message=f"yt-dlp timed out after {YT_DLP_TIMEOUT_SECONDS}s", category="timeout") from exc
            except Exception as exc:  # pragma: no cover - defensive runtime guard
                logger.exception("yt-dlp execution crashed", extra={"command": command})
                raise YouTubeDownloadError(
                    message=f"Failed to execute yt-dlp: {exc}",
                    category="execution_error",
                ) from exc

            last_result = result
            last_command = command
            print("YT-DLP STDOUT:", result.stdout)
            print("YT-DLP STDERR:", result.stderr)
            print("YT-DLP RETURN CODE:", result.returncode)
            logger.info("[YT-DLP STDOUT]", extra={"stdout": result.stdout})
            logger.info("[YT-DLP STDERR]", extra={"stderr": result.stderr})

            if _has_invalid_cookies_warning(result.stderr or "", result.stdout or ""):
                cookies_disabled = True
                logger.warning(
                    "[YTDLP_COOKIES_INVALID_WARNING] cookies inválidas/expiradas detectadas; próximas tentativas continuarão sem cookies",
                    extra={"attempt": attempt_index, "attempt_name": attempt["name"]},
                )

            if result.returncode == 0:
                final_format_match = re.search(r"\[REAL FINAL FORMAT\]\s*([^\n\r]+)", result.stdout or "")
                final_format_value = (final_format_match.group(1).strip() if final_format_match else "")
                logger.info(
                    "[YTDLP_FORMAT_SELECTED]",
                    extra={
                        "attempt": attempt_index,
                        "attempt_name": attempt["name"],
                        "format_selector": attempt["selector"],
                        "real_final_format": final_format_value or None,
                    },
                )
                break

            if attempt_index < len(format_attempts):
                logger.warning(
                    "[YTDLP_FORMAT_FALLBACK]",
                    extra={
                        "failed_attempt": attempt_index,
                        "failed_attempt_name": attempt["name"],
                        "next_attempt": attempt_index + 1,
                        "returncode": result.returncode,
                        "stderr": result.stderr,
                    },
                )
        else:
            result = last_result
            category, message = _classify_ytdlp_error(result.stderr if result else "", result.stdout if result else "")
            raw_error = (result.stderr or result.stdout or message if result else message).strip()
            logger.error(
                "[YOUTUBE DOWNLOAD ERROR] all yt-dlp format attempts failed",
                extra={
                    "command": last_command,
                    "stdout": result.stdout if result else "",
                    "stderr": result.stderr if result else "",
                    "returncode": result.returncode if result else None,
                    "error_category": category,
                },
            )
            raise YouTubeDownloadError(
                message=(
                    "Não foi possível baixar este vídeo do YouTube em nenhum formato disponível. "
                    "Tentamos H.264/AVC na qualidade solicitada, vídeo+áudio alternativo, bv*+ba/best e best. "
                    f"Detalhes do yt-dlp: {raw_error}"
                ),
                category=category,
            )

        logger.info(
            "[YOUTUBE DOWNLOAD SUCCESS] yt-dlp command finished",
            extra={"command": last_command, "returncode": last_result.returncode if last_result else 0, "error_category": "none"},
        )

        matches = sorted(
            [f for f in os.listdir(UPLOAD_DIR) if f.startswith(output_prefix)],
            key=lambda x: os.path.getmtime(os.path.join(UPLOAD_DIR, x)),
            reverse=True,
        )
        if not matches:
            logger.error("yt-dlp reported success but no output file was found", extra={"upload_dir": UPLOAD_DIR, "output_prefix": output_prefix})
            raise YouTubeDownloadError(
                message="Failed to locate downloaded YouTube video file.",
                category="missing_output",
            )
        output_file = os.path.join(UPLOAD_DIR, matches[0])
        output_file = _normalize_to_h264_mp4(output_file, ffmpeg_location)
        print(f"[PERF] yt_download = {time.perf_counter() - perf_start:.1f}s")

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
    finally:
        if os.path.exists(temp_cookie_file.name):
            os.unlink(temp_cookie_file.name)
