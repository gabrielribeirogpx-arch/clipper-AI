from fastapi import APIRouter, UploadFile, File
from app.jobs.process_video_job import process_video
from app.data.timeline_state import set_timeline_state
from app.schemas.upload import YoutubeIngestRequest
from app.services.youtube_service import download_youtube_video
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
    return _build_upload_response(transcription, file_id, filepath)


@router.post("/ingest/youtube")
async def ingest_youtube(payload: YoutubeIngestRequest):
    file_id = str(uuid.uuid4())
    filepath = download_youtube_video(
        payload.youtube_url,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )

    transcription = process_video(
        filepath,
        min_clip_length=payload.min_clip_length,
        max_clip_length=payload.max_clip_length,
    )

    return _build_upload_response(transcription, file_id, filepath)


def _build_upload_response(transcription, file_id: str, filepath: str):

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
        "clips": [
            {
                "viral_score": hook["viral_score"],
                "title_suggestion": hook.get("title_suggestion", ""),
                "clip_start": hook["start"],
                "clip_end": hook["end"],
                "emotional_score": hook["emotional_score"],
                "retention_score": hook["retention_score"],
                "preview_clip": hook["preview_clip"],
                "export_clip": hook["export_clip"],
            }
            for hook in hooks
        ],
    }
