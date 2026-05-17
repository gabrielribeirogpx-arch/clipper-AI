from datetime import datetime
from pathlib import Path
import re
import time

from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
import json
from app.jobs.process_video_job import process_video
from app.data.timeline_state import set_timeline_state
from app.services.youtube_service import download_youtube_video, YouTubeDownloadError
from app.data.ingest_jobs import cleanup_jobs, create_job, get_job, register_listener, unregister_listener, update_job
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


async def process_youtube_ingest_job(job_id: str, body: dict, output_dir: str) -> None:
    try:
        update_job(job_id, status="downloading", progress=10, step="Downloading YouTube video")
        filepath = await asyncio.to_thread(
            download_youtube_video,
            body["youtube_url"],
            body.get("start_time"),
            body.get("end_time"),
        )

        update_job(job_id, status="transcribing", progress=35, step="Transcribing audio")
        update_job(job_id, status="detecting", progress=55, step="Detecting best clips")
        update_job(job_id, status="rendering", progress=75, step="Rendering clips and metadata")

        transcription = await asyncio.to_thread(
            process_video,
            filepath,
            output_dir,
            int(body.get("min_clip_length", 30)),
            int(body.get("max_clip_length", 90)),
            25,
            0.45,
            0.6,
            lambda msg: print(msg),
        )

        response_payload = _build_upload_response(transcription, str(uuid.uuid4()), filepath)
        update_job(
            job_id,
            status="completed",
            progress=100,
            step="Completed",
            clips=response_payload.get("clips", []),
            result=response_payload,
        )
        print(f"[JOB COMPLETED] job_id={job_id}")
    except YouTubeDownloadError as error:
        update_job(job_id, status="failed", progress=100, step="Failed", error={"category": error.category, "message": error.message})
        print(f"[JOB FAILED] job_id={job_id} category={error.category} message={error.message}")
    except Exception as error:
        update_job(job_id, status="failed", progress=100, step="Failed", error={"category": "unknown", "message": str(error)})
        print(f"[JOB FAILED] job_id={job_id} error={error}")

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
async def ingest_youtube(request: Request):
    body = await request.json()
    youtube_url = (body.get("youtube_url") or "").strip()
    if not youtube_url:
        raise HTTPException(status_code=400, detail="youtube_url is required")

    analysis_folder = _resolve_analysis_folder(body.get("analysis_name"), body.get("output_folder"))
    output_dir = os.path.join(CLIPS_DIR, analysis_folder)
    os.makedirs(output_dir, exist_ok=True)

    analysis_id = analysis_folder
    job_id = str(uuid.uuid4())
    body["youtube_url"] = youtube_url
    create_job(job_id, analysis_id)
    asyncio.create_task(process_youtube_ingest_job(job_id, body, output_dir))
    return {"success": True, "job_id": job_id, "analysis_id": analysis_id, "status": "queued"}


@router.get("/ingest/status/{job_id}")
async def ingest_status(job_id: str):
    print(f"[FRONTEND REQUESTED JOB STATE] job_id={job_id}")
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return {k: job.get(k) for k in ["status", "progress", "step", "analysis_id", "clips", "error"]}


@router.get("/ingest/job/{job_id}")
async def ingest_job_state(job_id: str):
    print(f"[FRONTEND REQUESTED JOB STATE] job_id={job_id}")
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    print(f"[JOB RESTORED] job_id={job_id}")
    return {"job_id": job_id, **{k: job.get(k) for k in ["status", "progress", "step", "analysis_id", "clips", "finished", "error"]}}


@router.get("/ingest/stream/{job_id}")
async def ingest_stream(job_id: str):
    if not get_job(job_id):
        raise HTTPException(status_code=404, detail="job not found")

    async def event_generator():
        queue = register_listener(job_id)
        print(f"[SSE CLIENT CONNECTED] job_id={job_id}")
        try:
            while True:
                payload = await queue.get()
                data = {k: payload.get(k) for k in ["status", "progress", "step", "analysis_id", "clips", "error"]}
                yield f"event: progress\ndata: {json.dumps(data)}\n\n"
                if payload.get("status") in {"completed", "failed"}:
                    break
        finally:
            unregister_listener(job_id, queue)
            print(f"[SSE CLIENT DISCONNECTED] job_id={job_id}")

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.on_event("startup")
async def start_ingest_cleanup_task() -> None:
    async def _cleanup_loop():
        while True:
            cleanup_jobs()
            await asyncio.sleep(300)
    asyncio.create_task(_cleanup_loop())


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
                "raw_clip_path": _to_media_url(hook.get("raw_clip_path", hook["clip_path"])),
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
