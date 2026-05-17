from datetime import datetime
from pathlib import Path
import re

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from app.jobs.process_video_job import process_video
from app.data.timeline_state import set_timeline_state
from app.schemas.upload import YoutubeIngestRequest
from app.services.youtube_service import YouTubeDownloadError, download_youtube_video
import os
import uuid
import shutil

router = APIRouter()

UPLOAD_DIR = "app/uploads"
CLIPS_DIR = "app/clips"

os.makedirs(UPLOAD_DIR, exist_ok=True)


def _sanitize_analysis_folder(raw_name: str | None) -> str | None:
    if not raw_name:
        return None
    normalized = raw_name.strip().replace(" ", "_")
    normalized = normalized.replace("/", "_").replace("\\", "_")
    normalized = re.sub(r"[^a-zA-Z0-9_-]", "", normalized)
    normalized = normalized.strip("._-")
    if not normalized or normalized in {".", ".."}:
        return None
    return normalized


def _resolve_analysis_folder(analysis_name: str | None, output_folder: str | None) -> str:
    folder = _sanitize_analysis_folder(output_folder) or _sanitize_analysis_folder(analysis_name)
    if folder:
        return folder
    return datetime.utcnow().strftime("analysis_%Y%m%d_%H%M%S")


def _to_media_url(path: str) -> str:
    rel_path = Path(path).as_posix().replace("app/clips/", "", 1)
    return f"/media/{rel_path}"

@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    analysis_name: str | None = Form(default=None),
    output_folder: str | None = Form(default=None),
):

    file_id = str(uuid.uuid4())

    filepath = f"{UPLOAD_DIR}/{file_id}.mp4"

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    analysis_folder = _resolve_analysis_folder(analysis_name, output_folder)
    output_dir = os.path.join(CLIPS_DIR, analysis_folder)
    os.makedirs(output_dir, exist_ok=True)
    print(f"[ANALYSIS FOLDER CREATED] {output_dir}")

    transcription = process_video(filepath, output_dir=output_dir)
    return _build_upload_response(transcription, file_id, filepath)


@router.post("/ingest/youtube")
async def ingest_youtube(payload: YoutubeIngestRequest):
    file_id = str(uuid.uuid4())
    try:
        filepath = download_youtube_video(
            payload.youtube_url,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )
    except YouTubeDownloadError as error:
        raise HTTPException(status_code=400, detail={"error": error.message}) from error

    analysis_folder = _resolve_analysis_folder(payload.analysis_name, payload.output_folder)
    output_dir = os.path.join(CLIPS_DIR, analysis_folder)
    os.makedirs(output_dir, exist_ok=True)
    print(f"[ANALYSIS FOLDER CREATED] {output_dir}")

    transcription = process_video(
        filepath,
        output_dir=output_dir,
        min_clip_length=payload.min_clip_length,
        max_clip_length=payload.max_clip_length,
        max_clips=payload.max_clips,
        min_score=payload.min_score,
        overlap_tolerance=payload.overlap_tolerance,
    )

    return _build_upload_response(transcription, file_id, filepath)


def _build_upload_response(transcription, file_id: str, filepath: str):

    hooks = transcription["hooks"]
    duration = max([hook["end"] for hook in hooks], default=0.0)
    first_final_clip = hooks[0]["final_clip"] if hooks else filepath
    analysis_id = Path(hooks[0]["final_clip"]).parent.name if hooks else "default"

    set_timeline_state({
        "renderMode": "preview",
        "analysisId": analysis_id,
        "videoUrl": _to_media_url(first_final_clip),
        "previewVideoUrl": _to_media_url(first_final_clip),
        "exportVideoUrl": _to_media_url(first_final_clip),
        "duration": duration,
        "clips": [
            {
                "id": f"clip-{index}",
                "label": f"Clip {index + 1}",
                "start": hook["start"],
                "end": hook["end"],
                "duration": round(hook["end"] - hook["start"], 2),
                "clip_path": _to_media_url(hook["clip_path"]),
                "final_video": _to_media_url(hook["final_clip"]),
                "viral_score": hook["viral_score"],
                "hook_score": hook.get("hook_score", hook["viral_score"]),
                "retention_score": hook["retention_score"],
                "emotion_score": hook["emotional_score"],
                "title": hook.get("title_suggestion", ""),
                "caption": hook.get("caption_suggestion", ""),
                "description": hook.get("description_suggestion", ""),
                "hashtags": hook.get("hashtags", []),
                "emotion": hook.get("emotion", "neutro"),
                "category": hook.get("category", "curiosidade"),
                "viral_reason": hook.get("viral_reason", ""),
                "title_options": hook.get("title_options", []),
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
        "analysis_id": analysis_id,
        "video_url": _to_media_url(first_final_clip),
        "preview_video_url": _to_media_url(first_final_clip),
        "export_video_url": _to_media_url(first_final_clip),
        "timeline": transcription["timeline"],
        "project_id": file_id,
        "duration": duration,
        "clips": [
            {
                "clip_path": _to_media_url(hook["clip_path"]),
                "viral_score": hook["viral_score"],
                "hook_score": hook.get("hook_score", hook["viral_score"]),
                "title_suggestion": hook.get("title_suggestion", ""),
                "caption_suggestion": hook.get("caption_suggestion", ""),
                "description_suggestion": hook.get("description_suggestion", ""),
                "hashtags": hook.get("hashtags", []),
                "emotion": hook.get("emotion", "neutro"),
                "category": hook.get("category", "curiosidade"),
                "viral_reason": hook.get("viral_reason", ""),
                "title_options": hook.get("title_options", []),
                "clip_start": hook["start"],
                "clip_end": hook["end"],
                "emotional_score": hook["emotional_score"],
                "retention_score": hook["retention_score"],
                "duration": round(hook["end"] - hook["start"], 2),
                "final_clip": hook["final_clip"],
            }
            for hook in hooks
        ],
    }
