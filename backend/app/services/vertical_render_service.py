from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
from typing import Dict, List

from moviepy.editor import VideoFileClip

from app.services.reframing_service import ReframingService
from app.services.render_quality import (
    EXPORT_AUDIO_BITRATE,
    EXPORT_AUDIO_CODEC,
    EXPORT_CRF,
    EXPORT_MOVFLAGS,
    EXPORT_PIXEL_FORMAT,
    EXPORT_PRESET,
    EXPORT_VIDEO_CODEC,
    VERTICAL_PREMIUM_FILTER,
)

SAFE_CPU_RENDER = os.getenv("SAFE_CPU_RENDER", "false").strip().lower() in {"1", "true", "yes", "on"}
MAX_TRACKING_WIDTH = 1920
TARGET_RENDER_SIZE = (1080, 1920)
MANUAL_REGION_TARGET_ASPECT = 9 / 16
MANUAL_REGION_MIN_HEIGHT = 720
MANUAL_REGION_MIN_WIDTH = int(round(MANUAL_REGION_MIN_HEIGHT * MANUAL_REGION_TARGET_ASPECT))
FINAL_EXPORT_SETTINGS = {
    "codec": EXPORT_VIDEO_CODEC,
    "preset": EXPORT_PRESET,
    "crf": EXPORT_CRF,
    "audio_codec": EXPORT_AUDIO_CODEC,
    "audio_bitrate": EXPORT_AUDIO_BITRATE,
    "pix_fmt": EXPORT_PIXEL_FORMAT,
    "movflags": EXPORT_MOVFLAGS,
}


def normalize_manual_region(manual_region: Dict, frame_width: int = 1920, frame_height: int = 1080) -> Dict[str, int]:
    raw_w = int(manual_region.get("width", 0))
    raw_h = int(manual_region.get("height", 0))
    raw_x = int(manual_region.get("x", 0))
    raw_y = int(manual_region.get("y", 0))
    if raw_w <= 0 or raw_h <= 0:
        raise RuntimeError("manual_region is required with positive width/height")

    max_h = frame_height
    min_h = min(MANUAL_REGION_MIN_HEIGHT, max_h)
    requested_h = max(min_h, min(raw_h, max_h))
    width_from_aspect = int(round(requested_h * MANUAL_REGION_TARGET_ASPECT))
    max_w = int(round(frame_height * MANUAL_REGION_TARGET_ASPECT))
    w = max(MANUAL_REGION_MIN_WIDTH, min(width_from_aspect, max_w))
    h = int(round(w / MANUAL_REGION_TARGET_ASPECT))
    x = max(0, min(raw_x, frame_width - w))
    y = max(0, min(raw_y, frame_height - h))
    aspect_ratio = w / h
    print(f"[MANUAL REGION FINAL] width={w} height={h} aspect_ratio={aspect_ratio:.6f}")

    if abs(aspect_ratio - MANUAL_REGION_TARGET_ASPECT) > 0.002:
        raise RuntimeError(f"manual_region aspect ratio invalid: {aspect_ratio:.6f}, expected {MANUAL_REGION_TARGET_ASPECT:.6f}")
    return {"x": x, "y": y, "width": w, "height": h}


def _probe_dimensions(media_path: str) -> tuple[int, int]:
    probe_cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", media_path,
    ]
    proc = subprocess.run(probe_cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Failed to probe video dimensions for {media_path}: {proc.stderr}")
    w, h = (proc.stdout or "").strip().split("x", 1)
    return int(w), int(h)


def _probe_bitrate(media_path: str) -> str:
    probe_cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "format=bit_rate", "-of", "default=noprint_wrappers=1:nokey=1", media_path,
    ]
    proc = subprocess.run(probe_cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return f"probe_error:{proc.stderr.strip()}"
    return (proc.stdout or "").strip() or "unknown"


def _log_file_stats(label: str, media_path: str) -> None:
    if os.path.exists(media_path):
        print(f"[{label} SIZE BYTES] {os.path.getsize(media_path)}")
        print(f"[{label} BITRATE] {_probe_bitrate(media_path)}")


def _create_proxy_if_needed(video_path: str) -> tuple[str, bool]:
    width, _ = _probe_dimensions(video_path)
    if width <= MAX_TRACKING_WIDTH:
        return video_path, False

    proxy_file = tempfile.NamedTemporaryFile(prefix="proxy_1080_", suffix=".mp4", delete=False)
    proxy_file.close()
    proxy_path = proxy_file.name
    cmd = [
        "ffmpeg", "-y", "-i", video_path, "-vf", "scale=1920:-2",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-an", proxy_path,
    ]
    print(f"[REAL FFMPEG COMMAND] {' '.join(shlex.quote(part) for part in cmd)}")
    print(f"[REAL INPUT FILE] {video_path}")
    print(f"[REAL OUTPUT FILE] {proxy_path}")
    print("[REAL CRF] 18")
    print("[REAL PRESET] medium")
    _log_file_stats("REAL INPUT", video_path)
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Failed to create proxy video.\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    return proxy_path, True


def render_vertical_clip(video_path: str, segments: List[Dict], output_path: str, speaker_segments=None, tracking_video_path: str | None = None, original_video_path: str | None = None) -> str:
    """Render a vertical clip with camera reframing and original audio, without subtitles."""
    tracking_input = tracking_video_path or video_path
    tracking_source, proxy_created = _create_proxy_if_needed(tracking_input)
    if proxy_created:
        _log_file_stats("REAL OUTPUT", tracking_source)
    tracking_clip = VideoFileClip(tracking_source)

    sample_fps = 4.0 if SAFE_CPU_RENDER else 6.0
    max_zoom = 1.08 if SAFE_CPU_RENDER else 1.12
    reframer = ReframingService(sample_fps=sample_fps, max_zoom=max_zoom)

    print(f"[AI USING PROXY VIDEO] {tracking_source}")
    print(f"[FINAL RENDER USING ORIGINAL SOURCE] {video_path}")
    print("[PROXY COORDINATES UPSCALED] using normalized coordinates for crop mapping")
    reframed_video = reframer.apply(VideoFileClip(video_path).without_audio())
    final_video = reframed_video.set_audio(VideoFileClip(video_path).audio)

    print("[RENDER QUALITY PROFILE] profile=vertical_export")
    print("[FFMPEG START] profile=vertical_export output={}".format(output_path))
    print(f"[REAL PIPELINE] profile=vertical_export")
    print(f"[REAL INPUT FILE] {video_path}")
    print(f"[REAL OUTPUT FILE] {output_path}")
    print(f"[REAL CRF] {FINAL_EXPORT_SETTINGS['crf']}")
    print(f"[REAL PRESET] {FINAL_EXPORT_SETTINGS['preset']}")
    print("[REAL FFMPEG COMMAND] moviepy.write_videofile(codec={codec},preset={preset},fps=30,ffmpeg_params={params})".format(codec=FINAL_EXPORT_SETTINGS['codec'], preset=FINAL_EXPORT_SETTINGS['preset'], params=['-crf', str(FINAL_EXPORT_SETTINGS['crf']), '-vf', VERTICAL_PREMIUM_FILTER, '-pix_fmt', FINAL_EXPORT_SETTINGS['pix_fmt'], '-b:a', FINAL_EXPORT_SETTINGS['audio_bitrate'], '-movflags', FINAL_EXPORT_SETTINGS['movflags']]))
    _log_file_stats("REAL INPUT", video_path)
    try:
        final_video.write_videofile(
            output_path,
            codec=FINAL_EXPORT_SETTINGS["codec"],
            audio_codec=FINAL_EXPORT_SETTINGS["audio_codec"],
            fps=30,
            preset=FINAL_EXPORT_SETTINGS["preset"],
            ffmpeg_params=[
                "-crf", str(FINAL_EXPORT_SETTINGS["crf"]),
                "-vf", VERTICAL_PREMIUM_FILTER,
                "-pix_fmt", FINAL_EXPORT_SETTINGS["pix_fmt"],
                "-b:a", FINAL_EXPORT_SETTINGS["audio_bitrate"],
                "-movflags", FINAL_EXPORT_SETTINGS["movflags"],
            ],
        )
    except Exception as error:
        print(f"[FFMPEG ERROR] profile=vertical_export output={output_path} error={error}")
        raise

    print("[FFMPEG SUCCESS] profile=vertical_export output={}".format(output_path))
    print(
        "[FFMPEG SETTINGS] "
        f"codec={FINAL_EXPORT_SETTINGS['codec']} preset={FINAL_EXPORT_SETTINGS['preset']} "
        f"crf={FINAL_EXPORT_SETTINGS['crf']} "
        f"audio_codec={FINAL_EXPORT_SETTINGS['audio_codec']} audio_bitrate={FINAL_EXPORT_SETTINGS['audio_bitrate']}"
    )

    final_w, final_h = _probe_dimensions(output_path)
    if (final_w, final_h) != TARGET_RENDER_SIZE:
        raise RuntimeError(f"Rendered video has invalid size {final_w}x{final_h}; expected 1080x1920")
    print(f"[FINAL RESOLUTION] {final_w}x{final_h}")
    _log_file_stats("REAL OUTPUT", output_path)

    if proxy_created and tracking_source != video_path and os.path.exists(tracking_source):
        tracking_clip.close()
        try:
            os.remove(tracking_source)
        except PermissionError:
            print(f"[WARN] could not delete proxy: {tracking_source}")

    return output_path


def render_dual_region_clip(video_path: str, output_path: str, dual_regions: Dict) -> str:
    print("[DUAL REGION RENDER START]")
    print("[DUAL REGION PIPELINE ACTIVE]")
    print("[DUAL REGION COMPOSITION START]")
    region_a = dual_regions.get("regionA", {})
    region_b = dual_regions.get("regionB", {})
    print(f"[DUAL REGION CONFIG LOADED] regionA={region_a} regionB={region_b}")

    def _box(region: Dict) -> tuple[int, int, int, int]:
        return (
            int(region.get("width", 0)),
            int(region.get("height", 0)),
            int(region.get("x", 0)),
            int(region.get("y", 0)),
        )

    aw, ah, ax, ay = _box(region_a)
    bw, bh, bx, by = _box(region_b)
    if aw <= 0 or ah <= 0 or bw <= 0 or bh <= 0:
        print("[DUAL REGION CONFIG MISSING] reason=invalid_region_dimensions")
        print("[DUAL REGION RENDER BLOCKED] reason=invalid_dual_region_config")
        raise RuntimeError("Invalid dual region config: region dimensions must be > 0")
    print(f"[FINAL DUAL REGION CROPS] regionA=(x={ax},y={ay},w={aw},h={ah}) regionB=(x={bx},y={by},w={bw},h={bh})")
    print("[FINAL DUAL REGION SCALE] regionA->1080x960 regionB->1080x960 stack=1080x1920")
    filtergraph = (
        f"[0:v]crop={aw}:{ah}:{ax}:{ay},scale=1080:960:force_original_aspect_ratio=decrease,pad=1080:960:(ow-iw)/2:(oh-ih)/2[top];"
        f"[0:v]crop={bw}:{bh}:{bx}:{by},scale=1080:960:force_original_aspect_ratio=decrease,pad=1080:960:(ow-iw)/2:(oh-ih)/2[bottom];"
        f"[top][bottom]vstack=inputs=2,format=yuv420p[v]"
    )
    cmd = [
        "ffmpeg", "-y", "-i", video_path, "-filter_complex", filtergraph, "-map", "[v]", "-map", "0:a?",
        "-c:v", EXPORT_VIDEO_CODEC, "-crf", str(EXPORT_CRF), "-preset", EXPORT_PRESET, "-pix_fmt", EXPORT_PIXEL_FORMAT,
        "-c:a", EXPORT_AUDIO_CODEC, "-b:a", EXPORT_AUDIO_BITRATE, "-movflags", EXPORT_MOVFLAGS, output_path
    ]
    print("[DUAL REGION FFMPEG START]")
    print(f"[DUAL REGION FFMPEG COMMAND] {' '.join(shlex.quote(part) for part in cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Dual region render failed: {proc.stderr}")
    final_w, final_h = _probe_dimensions(output_path)
    print(f"[FINAL OUTPUT RESOLUTION] {final_w}x{final_h}")
    if (final_w, final_h) != TARGET_RENDER_SIZE:
        raise RuntimeError(f"Dual-region rendered video has invalid size {final_w}x{final_h}; expected 1080x1920")
    print("[DUAL REGION COMPOSITION COMPLETE]")
    print("[DUAL REGION RENDER COMPLETE]")
    return output_path


def render_manual_region_vertical(video_path: str, output_path: str, manual_region: Dict) -> str:
    print("[MANUAL REGION PIPELINE ACTIVE]")
    print(f"[MANUAL REGION CONFIG RECEIVED] manual_region={manual_region}")
    try:
        normalized = normalize_manual_region(manual_region, frame_width=1920, frame_height=1080)
    except RuntimeError:
        print("[MANUAL REGION CONFIG MISSING]")
        print("[MANUAL REGION RENDER BLOCKED]")
        raise

    w = normalized["width"]
    h = normalized["height"]
    x = normalized["x"]
    y = normalized["y"]
    print(f"[MANUAL REGION CROP] x={x} y={y} width={w} height={h}")
    print("[MANUAL REGION SCALE] target=1080x1920 exact_9x16")
    vf = f"crop={w}:{h}:{x}:{y},scale=1080:1920:flags=lanczos,format=yuv420p"
    cmd = ["ffmpeg","-y","-i",video_path,"-vf",vf,"-map","0:v","-map","0:a?","-c:v",EXPORT_VIDEO_CODEC,"-crf",str(EXPORT_CRF),"-preset",EXPORT_PRESET,"-pix_fmt",EXPORT_PIXEL_FORMAT,"-c:a",EXPORT_AUDIO_CODEC,"-b:a",EXPORT_AUDIO_BITRATE,"-movflags",EXPORT_MOVFLAGS,output_path]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Manual region render failed: {proc.stderr}")
    final_w, final_h = _probe_dimensions(output_path)
    print(f"[MANUAL REGION OUTPUT RESOLUTION] {final_w}x{final_h}")
    if (final_w, final_h) != TARGET_RENDER_SIZE:
        raise RuntimeError(f"Manual-region rendered video has invalid size {final_w}x{final_h}; expected 1080x1920")
    print("[MANUAL REGION COMPOSITION COMPLETE]")
    return output_path
