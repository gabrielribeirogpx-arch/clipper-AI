import os
import subprocess
import uuid

UPLOAD_DIR = "app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _format_download_section(start_time: str | None, end_time: str | None) -> str | None:
    if not start_time or not end_time:
        return None
    return f"*{start_time}-{end_time}"


def download_youtube_video(youtube_url: str, start_time: str | None = None, end_time: str | None = None) -> str:
    output_template = os.path.join(UPLOAD_DIR, f"yt_{uuid.uuid4()}_%(id)s.%(ext)s")
    command = [
        "yt-dlp",
        "--no-playlist",
        "-f",
        "mp4/bestvideo+bestaudio/best",
        "-o",
        output_template,
    ]

    section = _format_download_section(start_time, end_time)
    if section:
        command.extend(["--download-sections", section])

    command.append(youtube_url)
    subprocess.run(command, check=True)

    matches = sorted([f for f in os.listdir(UPLOAD_DIR) if f.startswith("yt_")], key=lambda x: os.path.getmtime(os.path.join(UPLOAD_DIR, x)), reverse=True)
    if not matches:
        raise RuntimeError("Failed to download YouTube video")
    return os.path.join(UPLOAD_DIR, matches[0])
