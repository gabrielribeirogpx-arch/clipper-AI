from fastapi import APIRouter, UploadFile, File
from app.jobs.process_video_job import process_video
from app.data.timeline_state import set_timeline_state
import os
import uuid
import shutil

router = APIRouter()

UPLOAD_DIR = "app/uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):

    file_id = str(uuid.uuid4())

    filepath = f"{UPLOAD_DIR}/{file_id}.mp4"

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    transcription = process_video(filepath)

    hooks = transcription["hooks"]
    duration = max([hook["end"] for hook in hooks], default=0.0)
    first_preview_clip = hooks[0]["preview_clip"] if hooks else filepath
    first_export_clip = hooks[0]["export_clip"] if hooks else filepath

    set_timeline_state({
        "renderMode": "preview",
        "videoUrl": f"/media/{os.path.basename(first_preview_clip)}",
        "previewVideoUrl": f"/media/{os.path.basename(first_preview_clip)}",
        "exportVideoUrl": f"/media/{os.path.basename(first_export_clip)}",
        "duration": duration,
        "clips": [
            {
                "id": f"clip-{index}",
                "label": f"Clip {index + 1}",
                "start": hook["start"],
                "end": hook["end"],
            }
            for index, hook in enumerate(hooks)
        ],
        "subtitles": transcription["timeline"]["subtitles"],
        "hooks": [
            {
                "id": f"hook-{index}",
                "label": "Hook",
                "start": hook["start"],
                "end": hook["end"],
                "text": hook["text"],
            }
            for index, hook in enumerate(hooks)
        ],
        "broll": transcription["timeline"]["broll"],
        "cuts": transcription["timeline"]["cuts"],
    })

    return {
        "success": True,
        "video_url": f"/media/{os.path.basename(first_preview_clip)}",
        "preview_video_url": f"/media/{os.path.basename(first_preview_clip)}",
        "export_video_url": f"/media/{os.path.basename(first_export_clip)}",
        "timeline": transcription["timeline"],
        "project_id": file_id,
        "duration": duration,
    }
