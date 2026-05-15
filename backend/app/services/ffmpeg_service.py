import subprocess
import os

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

    subprocess.run(command)

    return output_path