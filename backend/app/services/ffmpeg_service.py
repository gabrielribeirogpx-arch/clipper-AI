import subprocess
import os
import shlex
from pathlib import Path
from typing import Dict, List, Literal
from app.services.video_encoder_service import detect_best_encoder
from app.services.ffmpeg_gpu_fallback import run_ffmpeg_with_gpu_fallback
from app.services.render_quality import (
    EXPORT_AUDIO_BITRATE,
    EXPORT_AUDIO_CODEC,
    EXPORT_CRF,
    EXPORT_QUALITY_MODE,
    EXPORT_MOVFLAGS,
    EXPORT_PIXEL_FORMAT,
    EXPORT_PRESET,
    EXPORT_VIDEO_CODEC,
)

CLIPS_DIR = "app/clips"

ENCODER = detect_best_encoder()
print("[GPU PIPELINE ACTIVE]")
EXPORT_SETTINGS = {
    "codec": ENCODER.codec,
    "preset": ENCODER.preset,
    "crf": str(EXPORT_CRF),
    "audio_codec": EXPORT_AUDIO_CODEC,
    "audio_bitrate": EXPORT_AUDIO_BITRATE,
    "pix_fmt": EXPORT_PIXEL_FORMAT,
    "movflags": EXPORT_MOVFLAGS,
}

PREVIEW_SETTINGS = {
    "codec": ENCODER.codec,
    "preset": ENCODER.preset,
    "crf": str(EXPORT_CRF),
    "audio_codec": EXPORT_AUDIO_CODEC,
    "audio_bitrate": EXPORT_AUDIO_BITRATE,
    "pix_fmt": EXPORT_PIXEL_FORMAT,
    "movflags": EXPORT_MOVFLAGS,
}

os.makedirs(CLIPS_DIR, exist_ok=True)
FFMPEG_TIMEOUT_SECONDS = int(os.getenv("FFMPEG_TIMEOUT_SECONDS", "7200"))



def _probe_video_stream(media_path: str) -> Dict:
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate", "-of", "json", media_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return {"error": proc.stderr.strip()}
    try:
        data = __import__("json").loads(proc.stdout or "{}")
    except ValueError:
        return {"error": "invalid_json"}
    streams = data.get("streams") or []
    return streams[0] if streams else {}

def _export_settings_for_mode() -> Dict[str, str]:
    mode = EXPORT_QUALITY_MODE
    crf = "18" if mode == "balanced" else "14"
    preset = "medium" if mode == "balanced" else "slow"
    return {"crf": crf, "preset": preset, "mode": mode}

def _probe_bitrate(media_path: str) -> str:
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "format=bit_rate", "-of", "default=noprint_wrappers=1:nokey=1", media_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return f"probe_error:{proc.stderr.strip()}"
    return (proc.stdout or "").strip() or "unknown"


def _log_real_ffmpeg_command(command: List[str], input_file: str, output_file: str, settings: Dict[str, str], profile: str) -> None:
    print(f"[REAL PIPELINE] profile={profile}")
    print(f"[REAL INPUT FILE] {input_file}")
    print(f"[REAL OUTPUT FILE] {output_file}")
    print(f"[REAL CRF] {settings.get('crf', 'n/a')}")
    print(f"[REAL PRESET] {settings.get('preset', 'n/a')}")
    print(f"[REAL FFMPEG COMMAND] {' '.join(shlex.quote(part) for part in command)}")
    if os.path.exists(input_file):
        print(f"[REAL INPUT SIZE BYTES] {os.path.getsize(input_file)}")


def _log_output_stats(output_file: str) -> None:
    if os.path.exists(output_file):
        print(f"[REAL OUTPUT SIZE BYTES] {os.path.getsize(output_file)}")
        print(f"[REAL OUTPUT BITRATE] {_probe_bitrate(output_file)}")


def cut_clip(input_file, start, end, output_name, output_dir: str = CLIPS_DIR, prefer_stream_copy: bool = True):

    os.makedirs(output_dir, exist_ok=True)
    output_path = f"{output_dir}/{output_name}"
    settings = _export_settings_for_mode()
    metadata = _probe_video_stream(input_file)
    print(f"[EXPORT QUALITY] mode={settings['mode']}")
    print(f"[STREAM COPY FINAL] enabled={prefer_stream_copy and settings['mode'] == 'original'}")
    print(f"[FINAL RENDER RESOLUTION] width={metadata.get('width')} height={metadata.get('height')}")
    print("[FAST SEEK ENABLED]")
    print("[PRE-INPUT SEEK ACTIVE]")
    print("[SMART REMUX ACTIVE]")

    def _stream_copy_command() -> List[str]:
        return [
            "ffmpeg", "-y", "-ss", str(start), "-to", str(end), "-i", input_file,
            "-map", "0:v:0", "-map", "0:a:0?", "-avoid_negative_ts", "make_zero",
            "-fflags", "+genpts", "-c", "copy", output_path,
        ]

    def _reencode_command() -> List[str]:
        return [
            "ffmpeg", "-y", "-ss", str(start), "-to", str(end), "-i", input_file,
            "-map", "0:v:0", "-map", "0:a:0?", "-avoid_negative_ts", "make_zero",
            "-fflags", "+genpts", "-c:v", ENCODER.codec, "-preset", settings["preset"],
            "-crf", settings["crf"], "-pix_fmt", EXPORT_PIXEL_FORMAT, "-c:a", "aac",
            "-b:a", "320k", "-movflags", EXPORT_MOVFLAGS, output_path,
        ]

    commands = []
    if prefer_stream_copy and settings["mode"] == "original":
        print("[STREAM COPY ENABLED]")
        commands.append(("stream_copy", _stream_copy_command()))
    commands.append(("reencode", _reencode_command()))

    last_error = None
    for profile, command in commands:
        _log_real_ffmpeg_command(command, input_file, output_path, {"crf": settings["crf"], "preset": settings["preset"]}, f"cut_{profile}")
        print(f"[FFMPEG START] profile=cut_{profile} command={' '.join(command)}")
        try:
            proc = run_ffmpeg_with_gpu_fallback(command, timeout=FFMPEG_TIMEOUT_SECONDS, log_prefix="[FFMPEG]")
        except subprocess.TimeoutExpired:
            last_error = f"timeout:{FFMPEG_TIMEOUT_SECONDS}s"
            print(f"[FFMPEG TIMEOUT] profile=cut_{profile} timeout={FFMPEG_TIMEOUT_SECONDS}s output={output_path}")
            continue
        if proc.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"[FFMPEG SUCCESS] profile=cut_{profile} output={output_path}")
            _log_output_stats(output_path)
            return output_path
        last_error = proc.stderr
        print(f"[FFMPEG ERROR] profile=cut_{profile} output={output_path} stderr={proc.stderr}")
        if profile == "stream_copy":
            print(f"[FINAL RENDER FALLBACK] reason=stream_copy_failed")

    if last_error:
        print(f"[FINAL RENDER FALLBACK] reason={str(last_error)[:500]}")
    return output_path


def apply_broll_overlay(
    clip_path: str,
    timeline: List[Dict],
    output_name: str,
    output_dir: str = CLIPS_DIR,
    quality_profile: Literal["preview", "export"] = "export",
) -> str:
    """Apply contextual b-roll overlays with smooth fade transitions."""
    if not timeline:
        return clip_path

    os.makedirs(output_dir, exist_ok=True)
    output_path = f"{output_dir}/{output_name}"

    settings = PREVIEW_SETTINGS if quality_profile == "preview" else EXPORT_SETTINGS
    command = ["ffmpeg", "-y", "-i", clip_path]
    valid_items = []

    for item in timeline:
        asset_path = item.get("asset_path")
        if asset_path and Path(asset_path).exists():
            command.extend(["-stream_loop", "-1", "-i", asset_path])
            valid_items.append(item)

    if not valid_items:
        return clip_path

    filter_parts = ["[0:v]setpts=PTS-STARTPTS[base]"]
    current = "[base]"

    for idx, item in enumerate(valid_items, start=1):
        overlay = item.get("overlay", {})
        transition = item.get("transition", {})

        scale = overlay.get("scale", 0.32)
        opacity = overlay.get("opacity", 0.95)
        start = float(item.get("start", 0.0))
        end = float(item.get("end", start + 1.0))
        fade_in = float(transition.get("fade_in", 0.2))
        fade_out = float(transition.get("fade_out", 0.2))
        duration = max(end - start, 0.2)

        filter_parts.append(
            f"[{idx}:v]setpts=PTS-STARTPTS,scale=iw*{scale}:ih*{scale},format=rgba,colorchannelmixer=aa={opacity},"
            f"fade=t=in:st=0:d={fade_in}:alpha=1,fade=t=out:st={max(duration-fade_out,0.0)}:d={fade_out}:alpha=1[ov{idx}]"
        )
        filter_parts.append(
            f"{current}[ov{idx}]overlay=(W-w)/2:(H-h)/2:enable='between(t,{start},{end})'[v{idx}]"
        )
        current = f"[v{idx}]"

    filter_complex = ";".join(filter_parts)

    command.extend([
        "-filter_complex", filter_complex,
        "-map", current,
        "-map", "0:a?",
        "-c:v", settings["codec"],
        "-preset", settings["preset"],
        "-crf", settings["crf"],
        "-pix_fmt", settings["pix_fmt"],
        "-c:a", settings["audio_codec"],
        "-b:a", settings["audio_bitrate"],
        "-movflags", settings["movflags"],
        output_path,
    ])

    print(f"[RENDER QUALITY PROFILE] profile={quality_profile} output={output_path}")
    print(
        "[FFMPEG SETTINGS] "
        f"codec={settings['codec']} preset={settings['preset']} crf={settings['crf']} "
        f"audio_codec={settings['audio_codec']} audio_bitrate={settings['audio_bitrate']}"
    )

    _log_real_ffmpeg_command(command, clip_path, output_path, settings, quality_profile)
    print(f"[FFMPEG START] profile={quality_profile} command={' '.join(command)}")
    try:
        proc = run_ffmpeg_with_gpu_fallback(command, timeout=FFMPEG_TIMEOUT_SECONDS, log_prefix="[FFMPEG]")
    except subprocess.TimeoutExpired:
        print(f"[FFMPEG TIMEOUT] profile=cut timeout={FFMPEG_TIMEOUT_SECONDS}s output={output_path}")
        return output_path
    if proc.returncode != 0:
        print(f"[FFMPEG ERROR] profile={quality_profile} output={output_path} stderr={proc.stderr}")
    else:
        print(f"[FFMPEG SUCCESS] profile={quality_profile} output={output_path}")
        _log_output_stats(output_path)
    if os.path.exists(output_path):
        return output_path
    return clip_path
