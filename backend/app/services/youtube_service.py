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
from fractions import Fraction
from dataclasses import dataclass

from app.services.ffmpeg_gpu_fallback import run_ffmpeg_with_gpu_fallback

UPLOAD_DIR = "app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
QUALITY_HEIGHTS = {
    "720p": 720,
    "1080p": 1080,
    "4k": 2160,
}

YT_DLP_TIMEOUT_SECONDS = int(os.getenv("YT_DLP_TIMEOUT_SECONDS", "7200"))
NO_VIDEO_FORMATS_MESSAGE = (
    "O YouTube não liberou formatos de vídeo para este link. "
    "Atualize o yt-dlp, remova cookies expirados ou tente upload local."
)
YOUTUBE_SCAN_CLIENTS = ("android", "tv", "web")

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
    selection_reason: str | None


class FormatSelector:
    """Select yt-dlp formats from a JSON scan without relying on textual selectors."""

    CODEC_PRIORITY = (
        ("h264", ("avc1", "h264")),
        ("vp9", ("vp9",)),
        ("av1", ("av01", "av1")),
    )
    CODEC_SCORE = {"h264": 3, "vp9": 2, "av1": 1, "other": 0}

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

    def _height(self, format_info: dict) -> int | None:
        height = int(self._to_number(format_info.get("height"), 0))
        return height if height > 0 else None

    def _video_sort_key(self, format_info: dict) -> tuple:
        height = self._height(format_info) or 0
        width = int(self._to_number(format_info.get("width"), 0))
        fps = self._to_number(format_info.get("fps"), 0)
        tbr = self._to_number(format_info.get("tbr") or format_info.get("vbr"), 0)
        filesize = self._to_number(format_info.get("filesize") or format_info.get("filesize_approx"), 0)
        codec_score = self.CODEC_SCORE.get(self._codec_bucket(format_info.get("vcodec")) or "other", 0)
        return (height, width, codec_score, fps, tbr, filesize)

    def _audio_sort_key(self, format_info: dict) -> tuple:
        abr = self._to_number(format_info.get("abr"), 0)
        tbr = self._to_number(format_info.get("tbr"), 0)
        filesize = self._to_number(format_info.get("filesize") or format_info.get("filesize_approx"), 0)
        ext_score = 1 if str(format_info.get("ext") or "").lower() in {"m4a", "mp4"} else 0
        return (abr, tbr, ext_score, filesize)

    @staticmethod
    def scan_counts(info: dict) -> tuple[int, int, int]:
        formats = info.get("formats", []) if isinstance(info, dict) else []
        dict_formats = [fmt for fmt in formats if isinstance(fmt, dict)]
        video_formats = [fmt for fmt in dict_formats if FormatSelector._has_video(fmt)]
        audio_formats = [fmt for fmt in dict_formats if FormatSelector._has_audio(fmt)]
        return (len(dict_formats), len(video_formats), len(audio_formats))

    @staticmethod
    def _format_sample(formats: list[dict], limit: int = 10) -> list[dict]:
        return [
            {
                "format_id": fmt.get("format_id"),
                "ext": fmt.get("ext"),
                "vcodec": fmt.get("vcodec"),
                "acodec": fmt.get("acodec"),
                "height": fmt.get("height"),
                "resolution": fmt.get("resolution"),
            }
            for fmt in formats[:limit]
        ]

    @staticmethod
    def scan_audit_counts(info: dict) -> dict:
        formats = info.get("formats", []) if isinstance(info, dict) else []
        dict_formats = [fmt for fmt in formats if isinstance(fmt, dict)]
        video_formats = [fmt for fmt in dict_formats if FormatSelector._has_video(fmt)]
        audio_formats = [fmt for fmt in dict_formats if FormatSelector._has_audio(fmt)]
        adaptive_formats = [fmt for fmt in dict_formats if FormatSelector._has_video(fmt) != FormatSelector._has_audio(fmt)]
        progressive_formats = [fmt for fmt in dict_formats if FormatSelector._has_video(fmt) and FormatSelector._has_audio(fmt)]
        codec_counts = {"h264_count": 0, "vp9_count": 0, "av1_count": 0}
        for fmt in video_formats:
            bucket = FormatSelector._codec_bucket(fmt.get("vcodec"))
            if bucket in {"h264", "vp9", "av1"}:
                codec_counts[f"{bucket}_count"] += 1
        return {
            "total_formats": len(dict_formats),
            "video_formats": len(video_formats),
            "audio_formats": len(audio_formats),
            "adaptive_formats": len(adaptive_formats),
            "progressive_formats": len(progressive_formats),
            **codec_counts,
        }

    @staticmethod
    def log_available_formats(info: dict) -> None:
        formats = info.get("formats", []) if isinstance(info, dict) else []
        dict_formats = [fmt for fmt in formats if isinstance(fmt, dict)]
        logger.info("================ AVAILABLE FORMATS ================", extra={"total": len(dict_formats)})
        for fmt in dict_formats:
            logger.info(
                "AVAILABLE_FORMAT",
                extra={
                    "id": fmt.get("format_id"),
                    "format_id": fmt.get("format_id"),
                    "resolution": fmt.get("resolution"),
                    "width": fmt.get("width"),
                    "height": fmt.get("height"),
                    "fps": fmt.get("fps"),
                    "ext": fmt.get("ext"),
                    "vcodec": fmt.get("vcodec"),
                    "acodec": fmt.get("acodec"),
                    "tbr": fmt.get("tbr"),
                    "vbr": fmt.get("vbr"),
                    "abr": fmt.get("abr"),
                    "container": fmt.get("container"),
                    "format_note": fmt.get("format_note"),
                    "protocol": fmt.get("protocol"),
                },
            )
        logger.info("===================================================")

    def _log_rejected(self, reason: str, format_info: dict, selected_format_id: str | None = None) -> None:
        logger.info(
            "FORMAT_REJECTED",
            extra={
                "reason": reason,
                "id": format_info.get("format_id"),
                "format_id": format_info.get("format_id"),
                "selected_format_id": selected_format_id,
                "resolution": format_info.get("resolution"),
                "width": format_info.get("width"),
                "vcodec": format_info.get("vcodec"),
                "acodec": format_info.get("acodec"),
                "height": format_info.get("height"),
                "fps": format_info.get("fps"),
                "ext": format_info.get("ext"),
            },
        )

    def _rejection_reason(self, fmt: dict, selected: dict) -> str:
        if not fmt.get("format_id"):
            return "missing_format_id"
        if not self._has_video(fmt):
            return "no_video"
        height = self._height(fmt)
        selected_height = self._height(selected) or 0
        if height is None:
            return "missing_metadata_height"
        if height > self.max_height:
            return "height_above_requested"
        if height < selected_height:
            return "lower_resolution_than_selected"
        codec_score = self.CODEC_SCORE.get(self._codec_bucket(fmt.get("vcodec")) or "other", 0)
        selected_codec_score = self.CODEC_SCORE.get(self._codec_bucket(selected.get("vcodec")) or "other", 0)
        if height == selected_height and codec_score < selected_codec_score:
            return "codec_lower_priority_than_selected_at_same_resolution"
        if self._video_sort_key(fmt) < self._video_sort_key(selected):
            return "lower_sort_key_than_selected"
        return "not_selected"

    def _select_best_video(self, videos: list[dict]) -> tuple[dict | None, str | None]:
        known_height_videos = [
            fmt for fmt in videos
            if self._height(fmt) is not None and self._height(fmt) <= self.max_height
        ]
        if known_height_videos:
            return max(known_height_videos, key=self._video_sort_key), "highest_resolution_under_requested_preferring_h264_at_same_resolution"
        unknown_height_videos = [fmt for fmt in videos if self._height(fmt) is None]
        if unknown_height_videos:
            return max(unknown_height_videos, key=self._video_sort_key), "missing_height_metadata_best_available"
        if videos:
            return min(videos, key=self._video_sort_key), "all_formats_above_requested_lowest_above_requested"
        return None, None

    def select(self, info: dict) -> SelectedFormat:
        raw_formats = info.get("formats", []) if isinstance(info, dict) else []
        dict_formats = [fmt for fmt in raw_formats if isinstance(fmt, dict)]
        formats = []
        videos = []
        for fmt in dict_formats:
            if not fmt.get("format_id"):
                self._log_rejected("missing_format_id", fmt)
                continue
            formats.append(fmt)
            if not self._has_video(fmt):
                self._log_rejected("no_video", fmt)
                continue
            videos.append(fmt)

        if not videos:
            total_formats, video_format_count, _audio_format_count = self.scan_counts(info)
            sample = self._format_sample(dict_formats)
            raise YouTubeDownloadError(
                message=(
                    "Nenhum formato de vídeo encontrado após varredura yt-dlp -J. "
                    f"total_formats={total_formats}, formats_with_vcodec={video_format_count}, "
                    f"sample_first_10={json.dumps(sample, ensure_ascii=False)}"
                ),
                category="format_unavailable",
            )

        selected_video, selection_reason = self._select_best_video(videos)
        if selected_video is None:
            raise YouTubeDownloadError(
                message=f"Nenhum formato de vídeo selecionável encontrado após varredura yt-dlp -J. total_formats={len(dict_formats)}",
                category="format_unavailable",
            )

        audio_format_id = None
        if not self._has_audio(selected_video):
            audios = [fmt for fmt in formats if self._has_audio(fmt) and not self._has_video(fmt)]
            if audios:
                audio_format_id = str(max(audios, key=self._audio_sort_key)["format_id"])

        video_format_id = str(selected_video["format_id"])
        for fmt in formats:
            if str(fmt.get("format_id")) != video_format_id:
                self._log_rejected(self._rejection_reason(fmt, selected_video), fmt, video_format_id)
        logger.info(
            "FORMAT_SELECTED",
            extra={
                "id": video_format_id,
                "format_id": video_format_id,
                "resolution": selected_video.get("resolution"),
                "vcodec": selected_video.get("vcodec"),
                "codec": self._codec_bucket(selected_video.get("vcodec")),
                "height": self._height(selected_video),
                "width": selected_video.get("width"),
                "ext": selected_video.get("ext"),
                "reason": selection_reason,
                "fps": selected_video.get("fps"),
                "tbr": selected_video.get("tbr"),
            },
        )
        download_format = f"{video_format_id}+{audio_format_id}" if audio_format_id else video_format_id
        return SelectedFormat(
            video_format_id=video_format_id,
            audio_format_id=audio_format_id,
            download_format=download_format,
            video_codec=str(selected_video.get("vcodec") or ""),
            height=self._height(selected_video),
            ext=str(selected_video.get("ext") or "") or None,
            fps=self._to_number(selected_video.get("fps"), 0) or None,
            tbr=self._to_number(selected_video.get("tbr") or selected_video.get("vbr"), 0) or None,
            selection_reason=selection_reason,
        )


def _youtube_extractor_args(client: str | None) -> str | None:
    if not client:
        return None
    return f"youtube:player_client={client}"


def _build_json_scan_command(
    base_command: list[str],
    youtube_url: str,
    cookies_runtime_path: str | None,
    youtube_client: str | None = None,
) -> list[str]:
    command = [*base_command, "-J"]
    extractor_args = _youtube_extractor_args(youtube_client)
    if extractor_args:
        command.extend(["--extractor-args", extractor_args])
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


def _run_format_scan(
    base_command: list[str],
    youtube_url: str,
    normalized_quality: str,
    cookies_runtime_path: str | None,
    youtube_client: str | None = None,
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    scan_command = _build_json_scan_command(
        base_command=base_command,
        youtube_url=youtube_url,
        cookies_runtime_path=cookies_runtime_path,
        youtube_client=youtube_client,
    )
    logger.info(
        "FORMAT_SCAN_START",
        extra={
            "requested_quality": normalized_quality,
            "max_height": FormatSelector(normalized_quality).max_height,
            "using_cookies": bool(cookies_runtime_path),
            "youtube_client": youtube_client,
            "command": scan_command,
        },
    )
    try:
        return (
            subprocess.run(
                scan_command,
                check=False,
                capture_output=True,
                text=True,
                timeout=YT_DLP_TIMEOUT_SECONDS,
            ),
            scan_command,
        )
    except subprocess.TimeoutExpired as exc:
        logger.error("[YOUTUBE FORMAT SCAN TIMEOUT]", extra={"timeout_seconds": YT_DLP_TIMEOUT_SECONDS, "youtube_client": youtube_client})
        raise YouTubeDownloadError(message=f"yt-dlp -J timed out after {YT_DLP_TIMEOUT_SECONDS}s", category="timeout") from exc
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        logger.exception("yt-dlp format scan crashed", extra={"command": scan_command, "youtube_client": youtube_client})
        raise YouTubeDownloadError(
            message=f"Failed to execute yt-dlp -J: {exc}",
            category="execution_error",
        ) from exc


def _parse_format_scan_result(
    scan_result: subprocess.CompletedProcess[str],
    scan_command: list[str],
    normalized_quality: str,
    youtube_client: str | None,
) -> dict:
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
                "youtube_client": youtube_client,
            },
        )
        raise YouTubeDownloadError(message=f"Não foi possível obter formatos via yt-dlp -J. Detalhes: {raw_error}", category=category)

    try:
        format_info = json.loads(scan_result.stdout or "{}")
    except json.JSONDecodeError as exc:
        logger.error("[YOUTUBE FORMAT SCAN JSON_ERROR]", extra={"stdout": (scan_result.stdout or "")[:2000], "youtube_client": youtube_client})
        raise YouTubeDownloadError(message="yt-dlp -J returned invalid JSON while scanning formats.", category="format_scan_json") from exc

    total_formats, video_formats, audio_formats = FormatSelector.scan_counts(format_info)
    audit_counts = FormatSelector.scan_audit_counts(format_info)
    FormatSelector.log_available_formats(format_info)
    logger.info("SCAN CLIENT = %s", youtube_client or "default")
    logger.info(
        "FORMAT_SCAN_RESULT",
        extra={
            "total_formats": total_formats,
            "video_formats": video_formats,
            "audio_formats": audio_formats,
            **audit_counts,
            "requested_quality": normalized_quality,
            "youtube_client": youtube_client,
            "video_id": format_info.get("id") if isinstance(format_info, dict) else None,
        },
    )
    if video_formats == 0:
        sample = FormatSelector._format_sample(format_info.get("formats", []) if isinstance(format_info, dict) else [])
        logger.warning(
            "FORMAT_SCAN_NO_VIDEO_FORMATS",
            extra={
                "total_formats": total_formats,
                "audio_formats": audio_formats,
                "youtube_client": youtube_client,
                "sample_first_10": sample,
            },
        )
    return format_info


def _build_download_command(
    base_command: list[str],
    format_id_selector: str,
    output_template: str,
    youtube_url: str,
    ffmpeg_location: str | None,
    section: str | None,
    cookies_runtime_path: str | None,
    youtube_client: str | None = None,
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
    extractor_args = _youtube_extractor_args(youtube_client)
    if extractor_args:
        command.extend(["--extractor-args", extractor_args])
    if cookies_runtime_path:
        command.extend(["--cookies", cookies_runtime_path])
    if ffmpeg_location:
        command.extend(["--ffmpeg-location", ffmpeg_location])
    if section:
        command.extend(["--download-sections", section])
    command.append(youtube_url)
    return command


def _ffprobe_media_metadata(media_path: str, ffprobe_location: str | None = None) -> dict:
    ffprobe = ffprobe_location or shutil.which("ffprobe")
    if not ffprobe:
        return {"probe_error": "ffprobe_not_found"}
    probe_cmd = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,codec_name,avg_frame_rate,bit_rate:format=bit_rate,duration,format_name",
        "-of",
        "json",
        media_path,
    ]
    probe_result = subprocess.run(probe_cmd, check=False, capture_output=True, text=True)
    if probe_result.returncode != 0:
        return {"probe_error": probe_result.stderr}
    try:
        data = json.loads(probe_result.stdout or "{}")
    except json.JSONDecodeError:
        return {"probe_error": "invalid_json", "stdout": probe_result.stdout}
    stream = (data.get("streams") or [{}])[0]
    fmt = data.get("format") or {}
    fps = stream.get("avg_frame_rate")
    if fps and fps != "0/0":
        try:
            fps = float(Fraction(fps))
        except (ValueError, ZeroDivisionError):
            pass
    return {
        "width": stream.get("width"),
        "height": stream.get("height"),
        "codec": stream.get("codec_name"),
        "bitrate": stream.get("bit_rate") or fmt.get("bit_rate"),
        "fps": fps,
        "duration": fmt.get("duration"),
        "container": fmt.get("format_name"),
    }


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
        "-vf",
        "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
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
    normalize_result = run_ffmpeg_with_gpu_fallback(nvenc_cmd, log_prefix="[YOUTUBE NORMALIZE FFMPEG]")
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
        selected_youtube_client = None
        scan_result, scan_command = _run_format_scan(
            base_command=base_command,
            youtube_url=youtube_url,
            normalized_quality=normalized_quality,
            cookies_runtime_path=active_cookies,
            youtube_client=selected_youtube_client,
        )

        if _has_invalid_cookies_warning(scan_result.stderr or "", scan_result.stdout or ""):
            logger.warning("YTDLP_COOKIES_INVALID_WARNING", extra={"reason": "invalid_or_expired_cookies_detected"})
            logger.info("FORMAT_SCAN_RETRY_WITHOUT_COOKIES", extra={"reason": "invalid_cookies"})
            active_cookies = None
            scan_result, scan_command = _run_format_scan(
                base_command=base_command,
                youtube_url=youtube_url,
                normalized_quality=normalized_quality,
                cookies_runtime_path=None,
            )

        format_info = _parse_format_scan_result(scan_result, scan_command, normalized_quality, selected_youtube_client)
        total_formats, video_formats, _audio_formats = FormatSelector.scan_counts(format_info)

        if video_formats == 0 and active_cookies:
            logger.info("FORMAT_SCAN_RETRY_WITHOUT_COOKIES", extra={"reason": "no_video_formats", "total_formats": total_formats})
            active_cookies = None
            scan_result, scan_command = _run_format_scan(
                base_command=base_command,
                youtube_url=youtube_url,
                normalized_quality=normalized_quality,
                cookies_runtime_path=None,
            )
            if _has_invalid_cookies_warning(scan_result.stderr or "", scan_result.stdout or ""):
                logger.warning("YTDLP_COOKIES_INVALID_WARNING", extra={"reason": "invalid_cookies_after_cookie_free_retry"})
            format_info = _parse_format_scan_result(scan_result, scan_command, normalized_quality, selected_youtube_client)
            total_formats, video_formats, _audio_formats = FormatSelector.scan_counts(format_info)

        if video_formats == 0:
            for youtube_client in YOUTUBE_SCAN_CLIENTS:
                if selected_youtube_client:
                    logger.info("%s FAILED", selected_youtube_client.upper(), extra={"reason": "no_video_formats"})
                logger.info("Trying %s...", youtube_client.upper())
                logger.info(
                    "FORMAT_SCAN_RETRY_CLIENT",
                    extra={"youtube_client": youtube_client, "using_cookies": False, "reason": "no_video_formats"},
                )
                scan_result, scan_command = _run_format_scan(
                    base_command=base_command,
                    youtube_url=youtube_url,
                    normalized_quality=normalized_quality,
                    cookies_runtime_path=None,
                    youtube_client=youtube_client,
                )
                if _has_invalid_cookies_warning(scan_result.stderr or "", scan_result.stdout or ""):
                    logger.warning("YTDLP_COOKIES_INVALID_WARNING", extra={"reason": "client_retry_reported_cookie_warning", "youtube_client": youtube_client})
                format_info = _parse_format_scan_result(scan_result, scan_command, normalized_quality, youtube_client)
                total_formats, video_formats, _audio_formats = FormatSelector.scan_counts(format_info)
                if video_formats > 0:
                    active_cookies = None
                    selected_youtube_client = youtube_client
                    logger.info("%s SUCCESS", youtube_client.upper())
                    break
                logger.info("%s FAILED", youtube_client.upper(), extra={"reason": "no_video_formats"})

        if video_formats == 0:
            logger.error("FORMAT_SCAN_NO_VIDEO_FORMATS", extra={"reason": "all_retries_exhausted", "total_formats": total_formats})
            raise YouTubeDownloadError(message=NO_VIDEO_FORMATS_MESSAGE, category="format_unavailable")

        selected_format = FormatSelector(normalized_quality).select(format_info)
        logger.info(
            "FORMAT_SELECTED_BY_ID",
            extra={
                "format_id": selected_format.video_format_id,
                "video_format_id": selected_format.video_format_id,
                "audio_format_id": selected_format.audio_format_id,
                "download_format": selected_format.download_format,
                "vcodec": selected_format.video_codec,
                "height": selected_format.height,
                "ext": selected_format.ext,
                "reason": selected_format.selection_reason,
                "fps": selected_format.fps,
                "tbr": selected_format.tbr,
            },
        )
        logger.info(
            "DOWNLOAD FORMAT",
            extra={
                "id": selected_format.video_format_id,
                "resolution": f"{selected_format.height}p" if selected_format.height else None,
                "codec": selected_format.video_codec,
                "fps": selected_format.fps,
                "bitrate": selected_format.tbr,
                "container": selected_format.ext,
                "download_format": selected_format.download_format,
                "scan_client": selected_youtube_client or "default",
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
            youtube_client=selected_youtube_client,
        )
        logger.info("[REAL YT-DLP COMMAND]", extra={"purpose": "download", "command": command, "youtube_client": selected_youtube_client})
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
                metadata = _ffprobe_media_metadata(output_file, ffprobe_location)
                if "probe_error" in metadata:
                    logger.warning("[YOUTUBE SOURCE PROBE FAILED]", extra=metadata)
                else:
                    logger.info(
                        "DOWNLOADED FILE",
                        extra={
                            "width": metadata.get("width"),
                            "height": metadata.get("height"),
                            "resolution": f"{metadata.get('width')}x{metadata.get('height')}",
                            "codec": metadata.get("codec"),
                            "bitrate": metadata.get("bitrate"),
                            "fps": metadata.get("fps"),
                            "duration": metadata.get("duration"),
                            "container": metadata.get("container"),
                        },
                    )

        return output_file
    finally:
        if os.path.exists(temp_cookie_file.name):
            os.unlink(temp_cookie_file.name)
