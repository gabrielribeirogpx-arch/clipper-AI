import json
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





@dataclass(frozen=True)
class SelectedFormat:
    video_format_id: str
    audio_format_id: str | None
    download_format: str
    video_codec: str
    height: int | None
    ext: str | None
    fps: float | None
    tbr: float | None


class FormatSelector:
    """Select yt-dlp formats from a JSON scan without relying on textual selectors."""

    CODEC_PRIORITY = (
        ("h264", ("avc1", "h264")),
        ("vp9", ("vp9",)),
        ("av1", ("av01", "av1")),
    )

    def __init__(self, requested_quality: str) -> None:
        normalized_quality = (requested_quality or "1080p").strip().lower()
        self.max_height = QUALITY_HEIGHTS.get(normalized_quality, QUALITY_HEIGHTS["1080p"])
        self.requested_quality = normalized_quality

    @staticmethod
    def _to_number(value: object, default: float = 0.0) -> float:
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _codec_bucket(vcodec: object) -> str | None:
        codec = str(vcodec or "").lower()
        if not codec or codec == "none":
            return None
        for bucket, markers in FormatSelector.CODEC_PRIORITY:
            if any(marker in codec for marker in markers):
                return bucket
        return "other"

    @staticmethod
    def _has_video(format_info: dict) -> bool:
        return str(format_info.get("vcodec") or "none").lower() != "none"

    @staticmethod
    def _has_audio(format_info: dict) -> bool:
        return str(format_info.get("acodec") or "none").lower() != "none"

    def _video_sort_key(self, format_info: dict) -> tuple:
        height = int(self._to_number(format_info.get("height"), 0))
        width = int(self._to_number(format_info.get("width"), 0))
        fps = self._to_number(format_info.get("fps"), 0)
        tbr = self._to_number(format_info.get("tbr") or format_info.get("vbr"), 0)
        filesize = self._to_number(format_info.get("filesize") or format_info.get("filesize_approx"), 0)
        return (height, width, fps, tbr, filesize)

    def _audio_sort_key(self, format_info: dict) -> tuple:
        abr = self._to_number(format_info.get("abr"), 0)
        tbr = self._to_number(format_info.get("tbr"), 0)
        filesize = self._to_number(format_info.get("filesize") or format_info.get("filesize_approx"), 0)
        ext_score = 1 if str(format_info.get("ext") or "").lower() in {"m4a", "mp4"} else 0
        return (abr, tbr, ext_score, filesize)

    def select(self, info: dict) -> SelectedFormat:
        formats = [fmt for fmt in info.get("formats", []) if isinstance(fmt, dict) and fmt.get("format_id")]
        videos = [
            fmt for fmt in formats
            if self._has_video(fmt)
            and int(self._to_number(fmt.get("height"), 0)) > 0
            and int(self._to_number(fmt.get("height"), 0)) <= self.max_height
        ]
        if not videos:
            raise YouTubeDownloadError(
                message=f"Nenhum formato de vídeo encontrado até {self.max_height}p após varredura yt-dlp -J.",
                category="format_unavailable",
            )

        selected_video = None
        for bucket, _markers in self.CODEC_PRIORITY:
            candidates = [fmt for fmt in videos if self._codec_bucket(fmt.get("vcodec")) == bucket]
            if candidates:
                selected_video = max(candidates, key=self._video_sort_key)
                break
        if selected_video is None:
            selected_video = max(videos, key=self._video_sort_key)

        audio_format_id = None
        if not self._has_audio(selected_video):
            audios = [fmt for fmt in formats if self._has_audio(fmt) and not self._has_video(fmt)]
            if audios:
                audio_format_id = str(max(audios, key=self._audio_sort_key)["format_id"])

        video_format_id = str(selected_video["format_id"])
        download_format = f"{video_format_id}+{audio_format_id}" if audio_format_id else video_format_id
        return SelectedFormat(
            video_format_id=video_format_id,
            audio_format_id=audio_format_id,
            download_format=download_format,
            video_codec=str(selected_video.get("vcodec") or ""),
            height=int(self._to_number(selected_video.get("height"), 0)) or None,
            ext=str(selected_video.get("ext") or "") or None,
            fps=self._to_number(selected_video.get("fps"), 0) or None,
            tbr=self._to_number(selected_video.get("tbr") or selected_video.get("vbr"), 0) or None,
        )


def _build_json_scan_command(
    base_command: list[str],
    youtube_url: str,
    cookies_runtime_path: str | None,
) -> list[str]:
    command = [*base_command, "-J"]
    if cookies_runtime_path:
        command.extend(["--cookies", cookies_runtime_path])
    command.append(youtube_url)
    return command


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
    format_id_selector: str,
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
        format_id_selector,
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
    logger.info("FORMAT_NORMALIZATION", extra={"codec": codec_name, "format": format_name, "command": nvenc_cmd})
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

        active_cookies = cookies_runtime_path
        scan_command = _build_json_scan_command(
            base_command=base_command,
            youtube_url=youtube_url,
            cookies_runtime_path=active_cookies,
        )
        logger.info(
            "FORMAT_SCAN_START",
            extra={
                "requested_quality": normalized_quality,
                "max_height": FormatSelector(normalized_quality).max_height,
                "using_cookies": bool(active_cookies),
                "command": scan_command,
            },
        )
        try:
            scan_result = subprocess.run(
                scan_command,
                check=False,
                capture_output=True,
                text=True,
                timeout=YT_DLP_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            logger.error("[YOUTUBE FORMAT SCAN TIMEOUT]", extra={"timeout_seconds": YT_DLP_TIMEOUT_SECONDS})
            raise YouTubeDownloadError(message=f"yt-dlp -J timed out after {YT_DLP_TIMEOUT_SECONDS}s", category="timeout") from exc
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            logger.exception("yt-dlp format scan crashed", extra={"command": scan_command})
            raise YouTubeDownloadError(
                message=f"Failed to execute yt-dlp -J: {exc}",
                category="execution_error",
            ) from exc

        if _has_invalid_cookies_warning(scan_result.stderr or "", scan_result.stdout or ""):
            logger.warning("[YTDLP_COOKIES_INVALID_WARNING] cookies inválidas/expiradas detectadas; refazendo varredura sem cookies")
            active_cookies = None
            scan_command = _build_json_scan_command(
                base_command=base_command,
                youtube_url=youtube_url,
                cookies_runtime_path=None,
            )
            logger.info("FORMAT_SCAN_START", extra={"requested_quality": normalized_quality, "using_cookies": False, "command": scan_command})
            scan_result = subprocess.run(
                scan_command,
                check=False,
                capture_output=True,
                text=True,
                timeout=YT_DLP_TIMEOUT_SECONDS,
            )

        if scan_result.returncode != 0:
            category, message = _classify_ytdlp_error(scan_result.stderr or "", scan_result.stdout or "")
            raw_error = (scan_result.stderr or scan_result.stdout or message).strip()
            logger.error(
                "[YOUTUBE FORMAT SCAN ERROR]",
                extra={
                    "command": scan_command,
                    "stdout": scan_result.stdout,
                    "stderr": scan_result.stderr,
                    "returncode": scan_result.returncode,
                    "error_category": category,
                },
            )
            raise YouTubeDownloadError(message=f"Não foi possível obter formatos via yt-dlp -J. Detalhes: {raw_error}", category=category)

        try:
            format_info = json.loads(scan_result.stdout or "{}")
        except json.JSONDecodeError as exc:
            logger.error("[YOUTUBE FORMAT SCAN JSON_ERROR]", extra={"stdout": scan_result.stdout[:2000]})
            raise YouTubeDownloadError(message="yt-dlp -J returned invalid JSON while scanning formats.", category="format_scan_json") from exc

        available_formats = format_info.get("formats", []) if isinstance(format_info, dict) else []
        logger.info(
            "FORMAT_SCAN_RESULT",
            extra={
                "format_count": len(available_formats),
                "requested_quality": normalized_quality,
                "video_id": format_info.get("id") if isinstance(format_info, dict) else None,
            },
        )
        selected_format = FormatSelector(normalized_quality).select(format_info)
        logger.info(
            "FORMAT_SELECTED_BY_ID",
            extra={
                "video_format_id": selected_format.video_format_id,
                "audio_format_id": selected_format.audio_format_id,
                "download_format": selected_format.download_format,
                "vcodec": selected_format.video_codec,
                "height": selected_format.height,
                "ext": selected_format.ext,
                "fps": selected_format.fps,
                "tbr": selected_format.tbr,
            },
        )

        command = _build_download_command(
            base_command=base_command,
            format_id_selector=selected_format.download_format,
            output_template=output_template,
            youtube_url=youtube_url,
            ffmpeg_location=ffmpeg_location,
            section=section,
            cookies_runtime_path=active_cookies,
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

        print("YT-DLP STDOUT:", result.stdout)
        print("YT-DLP STDERR:", result.stderr)
        print("YT-DLP RETURN CODE:", result.returncode)
        logger.info("[YT-DLP STDOUT]", extra={"stdout": result.stdout})
        logger.info("[YT-DLP STDERR]", extra={"stderr": result.stderr})

        if result.returncode != 0:
            category, message = _classify_ytdlp_error(result.stderr or "", result.stdout or "")
            raw_error = (result.stderr or result.stdout or message).strip()
            logger.error(
                "[YOUTUBE DOWNLOAD ERROR] selected format_id download failed",
                extra={"command": command, "stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode, "error_category": category},
            )
            raise YouTubeDownloadError(
                message=(
                    "Não foi possível baixar o vídeo pelo format_id selecionado dinamicamente. "
                    "O download não depende de seletores textuais fixos do yt-dlp. "
                    f"Detalhes do yt-dlp: {raw_error}"
                ),
                category=category,
            )

        logger.info(
            "[YOUTUBE DOWNLOAD SUCCESS] yt-dlp command finished",
            extra={"command": command, "returncode": result.returncode, "error_category": "none"},
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
