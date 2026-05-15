import subprocess
import os
from pathlib import Path
from typing import Dict, List

CLIPS_DIR = "app/clips"

os.makedirs(CLIPS_DIR, exist_ok=True)


def cut_clip(input_file, start, end, output_name, subtitle_path=None):

    output_path = f"{CLIPS_DIR}/{output_name}"

    command = [
        "ffmpeg",
        "-y",
        "-i",
        input_file,
        "-ss",
        str(start),
        "-to",
        str(end),
    ]

    if subtitle_path:
        command.extend([
            "-vf",
            f"subtitles={subtitle_path}"
        ])

    command.extend([
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        output_path
    ])

    subprocess.run(command, check=False)

    return output_path


def apply_broll_overlay(clip_path: str, timeline: List[Dict], output_name: str) -> str:
    """Apply contextual b-roll overlays with smooth fade transitions."""
    if not timeline:
        return clip_path

    output_path = f"{CLIPS_DIR}/{output_name}"

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
        "-c:v", "libx264",
        "-c:a", "aac",
        output_path,
    ])

    subprocess.run(command, check=False)
    if os.path.exists(output_path):
        return output_path
    return clip_path
