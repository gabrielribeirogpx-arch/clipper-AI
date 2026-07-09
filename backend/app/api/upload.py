from datetime import datetime
from pathlib import Path
import os
import re
import time

from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
import json
from app.jobs.process_video_job import process_video
from app.data.timeline_state import set_timeline_state, save_timeline_state_for_analysis
from app.services.youtube_service import download_youtube_video, YouTubeDownloadError
from app.data.ingest_jobs import cleanup_jobs, create_job, get_job, register_listener, unregister_listener, update_job
from app.schemas.upload import YoutubeIngestRequest
import uuid
import threading
from dataclasses import dataclass
from app.services.ai_metadata_service import apply_metadata_to_clip, generate_metadata, max_clips, select_provider

router = APIRouter()

UPLOAD_DIR = "data/uploads"
CLIPS_DIR = "app/clips"
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
UPLOAD_CHUNK_SIZE = 1024 * 1024
INVALID_SAVE_FOLDER_MESSAGE = "Escolha uma pasta real para salvar os clipes."
_PLACEHOLDER_SAVE_FOLDER_TOKENS = ("<user>", "{user}", "%user%", "$user", "username", "your_username")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CLIPS_DIR, exist_ok=True)



def _looks_like_placeholder_path(path: str) -> bool:
    lowered = path.lower()
    return "<" in path or ">" in path or any(token in lowered for token in _PLACEHOLDER_SAVE_FOLDER_TOKENS)


def _sanitize_save_folder(save_folder: str | None, *, reject_invalid: bool = True) -> str | None:
    if save_folder is None:
        return None

    normalized = save_folder.strip()
    if not normalized:
        return None

    if _looks_like_placeholder_path(normalized):
        if reject_invalid:
            raise HTTPException(status_code=400, detail=INVALID_SAVE_FOLDER_MESSAGE)
        return None

    if not os.path.isabs(normalized):
        message = f"Caminho relativo ignorado para save_folder: '{normalized}'. Usando a pasta interna do app."
        print(f"[INVALID_SAVE_FOLDER_FALLBACK] {message}")
        return None

    return os.path.abspath(os.path.expanduser(normalized))


def _default_backend_save_folder() -> str:
    return os.path.abspath(CLIPS_DIR)


def _resolve_save_folder(save_folder: str | None, *, reject_invalid: bool = True) -> str:
    return _sanitize_save_folder(save_folder, reject_invalid=reject_invalid) or _default_backend_save_folder()

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


def _parse_time_to_seconds(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    parts = [float(part) for part in str(value).split(":")]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0]


def _safe_upload_extension(filename: str | None, content_type: str | None = None) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix in ALLOWED_VIDEO_EXTENSIONS:
        return suffix
    raise HTTPException(
        status_code=400,
        detail="Formato de vídeo inválido. Envie um arquivo .mp4, .mov, .mkv ou .webm.",
    )


def _sanitize_upload_filename(filename: str | None, fallback: str = "source") -> str:
    stem = Path(filename or fallback).stem.strip()
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "_", stem).strip("._-")
    return stem or fallback


async def _save_upload_file(file: UploadFile, analysis_id: str) -> str:
    extension = _safe_upload_extension(file.filename, file.content_type)
    upload_dir = Path(UPLOAD_DIR) / analysis_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    base_name = _sanitize_upload_filename(file.filename)
    destination = upload_dir / f"{base_name}{extension}"
    if destination.exists():
        destination = upload_dir / f"{base_name}_{uuid.uuid4().hex[:8]}{extension}"

    bytes_written = 0
    with destination.open("wb") as buffer:
        while True:
            chunk = await file.read(UPLOAD_CHUNK_SIZE)
            if not chunk:
                break
            bytes_written += len(chunk)
            buffer.write(chunk)

    if bytes_written == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="O arquivo enviado está vazio.")

    print(f"[LOCAL UPLOAD SAVED] analysis_id={analysis_id} filename={file.filename} path={destination} bytes={bytes_written}")
    return destination.as_posix()


@dataclass
class YouTubeSource:
    youtube_url: str
    start_time: str | None = None
    end_time: str | None = None
    video_quality: str = "1080p"

    async def to_local_file(self) -> str:
        return await asyncio.to_thread(
            download_youtube_video,
            self.youtube_url,
            self.start_time,
            self.end_time,
            self.video_quality,
        )


@dataclass
class LocalUploadSource:
    video_path: str

    async def to_local_file(self) -> str:
        return self.video_path


def _stream_progress_to_job(job_id: str):
    def _stream_event(event: dict) -> None:
        event_type = event.get("event")
        progress_by_event = {
            "PIPELINE_STAGE_STARTED": 20,
            "PIPELINE_STAGE_FINISHED": 45,
            "FIRST_CLIP_READY": 82,
            "EDITOR_READY": 85,
            "BACKGROUND_PROCESSING": 90,
            "CLIP_RENDERED": 92,
            "METADATA_READY": 96,
            "BACKGROUND_FINISHED": 99,
        }
        stage = event.get("stage") or event_type
        status = "processing"
        step = str(stage).replace("_", " ").title()
        clips = None
        if event.get("clip"):
            current = get_job(job_id) or {}
            raw_clips = current.get("_raw_clips", [])
            raw_clips = [*raw_clips, event["clip"]]
            clips = [_clip_response_item(hook, index) for index, hook in enumerate(raw_clips)]
            update_job(job_id, _raw_clips=raw_clips)
        if event_type == "FIRST_CLIP_READY":
            status = "editor_ready"
            step = "Editor disponível — gerando mais clipes em background"
        elif event_type == "BACKGROUND_PROCESSING":
            status = "background_processing"
            step = "Você já pode editar enquanto continuamos processando."
        update_job(job_id, status=status, progress=progress_by_event.get(event_type, 50), step=step, clips=clips if clips is not None else (get_job(job_id) or {}).get("clips", []), pipeline_event=event)

    return _stream_event


async def _run_process_video_source(job_id: str, body: dict, output_dir: str, source, source_type: str, initial_step: str) -> None:
    try:
        update_job(job_id, status="preparing", progress=8, step=initial_step)
        filepath = await source.to_local_file()
        render_mode = body.get("render_mode", "ai_tracking")
        print(f"[PROCESS VIDEO SOURCE] source_type={source_type} analysis_id={(get_job(job_id) or {}).get('analysis_id')} video_path={filepath}")
        print(f"[BACKEND RECEIVED RENDER MODE] source={source_type} render_mode={render_mode}")
        print(f"[PROCESS VIDEO JOB MODE] {source_type}_processing_render_mode={render_mode}")
        print(f"[PROCESS VIDEO JOB CONFIG] {source_type}_dual_region_config={body.get('dual_region_config')}")
        update_job(job_id, status="processing", progress=15, step="Processando vídeo")

        transcription = await asyncio.to_thread(
            process_video,
            filepath,
            output_dir=output_dir,
            render_mode=render_mode,
            dual_region_config=body.get("dual_region_config"),
            source_start_time=0 if source_type == "youtube" else (_parse_time_to_seconds(body.get("source_start_time")) or 0),
            source_end_time=None if source_type == "youtube" else _parse_time_to_seconds(body.get("source_end_time")),
            min_clip_length=int(body.get("min_clip_length", 30)),
            max_clip_length=int(body.get("max_clip_length", 90)),
            max_clips=25,
            min_score=0.45,
            overlap_tolerance=0.6,
            step_logger=lambda msg: print(f"[PIPELINE source_type={source_type}] {msg}"),
            original_video_path=filepath,
            auto_save_dir=_resolve_save_folder(body.get("save_folder"), reject_invalid=False),
            event_logger=_stream_progress_to_job(job_id),
        )

        update_job(job_id, status="processing", progress=96, step="Gerando clipes")
        response_payload = _build_upload_response(transcription, str(uuid.uuid4()), filepath, render_mode=render_mode, video_quality=body.get("video_quality", "1080p"))
        if response_payload.get("status") == "waiting_dual_region":
            update_job(job_id, status="waiting_dual_region", progress=100, step="Waiting dual-region setup", clips=response_payload.get("clips", []), result=response_payload)
            print(f"[JOB WAITING DUAL REGION] job_id={job_id} source_type={source_type}")
        else:
            update_job(job_id, status="completed", progress=100, step="Upload concluído" if source_type == "upload" else "Completed", clips=response_payload.get("clips", []), result=response_payload)
            print(f"[JOB COMPLETED] job_id={job_id} source_type={source_type}")
    except YouTubeDownloadError as error:
        update_job(job_id, status="failed", progress=100, step="Failed", error={"category": error.category, "message": error.message})
        print(f"[JOB FAILED] job_id={job_id} source_type={source_type} category={error.category} message={error.message}")
    except Exception as error:
        update_job(job_id, status="failed", progress=100, step="Failed", error={"category": "unknown", "message": str(error)})
        print(f"[JOB FAILED] job_id={job_id} source_type={source_type} error={error}")


async def process_youtube_ingest_job(job_id: str, body: dict, output_dir: str) -> None:
    print(f"[SOURCE_INTERVAL_SELECTED] source_start_time={body.get('source_start_time') or body.get('start_time')} source_end_time={body.get('source_end_time') or body.get('end_time')}")
    source = YouTubeSource(
        youtube_url=body["youtube_url"],
        start_time=body.get("source_start_time") or body.get("start_time"),
        end_time=body.get("source_end_time") or body.get("end_time"),
        video_quality=body.get("video_quality", "1080p"),
    )
    await _run_process_video_source(job_id, body, output_dir, source, "youtube", "Preparando análise")

async def process_upload_ingest_job(job_id: str, body: dict, output_dir: str, filepath: str) -> None:
    print(f"[SOURCE_INTERVAL_SELECTED] source_start_time={body.get('source_start_time')} source_end_time={body.get('source_end_time')}")
    await _run_process_video_source(job_id, body, output_dir, LocalUploadSource(filepath), "upload", "Preparando análise")


@router.post("/upload")
@router.post("/api/upload")
async def upload_video(
    file: UploadFile = File(...),
    analysis_name: str | None = Form(default=None),
    output_folder: str | None = Form(default=None),
    render_mode: str = Form(default="ai_tracking"),
    video_quality: str = Form(default="1080p"),
    save_folder: str | None = Form(default=None),
    source_start_time: str | None = Form(default=None),
    source_end_time: str | None = Form(default=None),
    min_clip_length: int = Form(default=30),
    max_clip_length: int = Form(default=90),
):
    analysis_folder = _resolve_analysis_folder(analysis_name, output_folder)
    analysis_id = analysis_folder
    output_dir = os.path.join(CLIPS_DIR, analysis_folder)
    os.makedirs(output_dir, exist_ok=True)
    print(f"[ANALYSIS FOLDER CREATED] {output_dir}")
    filepath = await _save_upload_file(file, analysis_id)
    job_id = str(uuid.uuid4())
    body = {
        "render_mode": render_mode,
        "video_quality": video_quality,
        "save_folder": _resolve_save_folder(save_folder),
        "source_start_time": source_start_time,
        "source_end_time": source_end_time,
        "min_clip_length": min_clip_length,
        "max_clip_length": max_clip_length,
    }
    create_job(job_id, analysis_id)
    asyncio.create_task(process_upload_ingest_job(job_id, body, output_dir, filepath))
    return {"success": True, "job_id": job_id, "analysis_id": analysis_id, "status": "uploaded"}


@router.post("/ingest/youtube")
async def ingest_youtube(request: Request):
    body = await request.json()
    print(f"[INGEST RAW REQUEST BODY] {body}")
    payload = YoutubeIngestRequest.model_validate(body)
    youtube_url = (payload.youtube_url or "").strip()
    if not youtube_url:
        raise HTTPException(status_code=400, detail="youtube_url is required")

    analysis_folder = _resolve_analysis_folder(payload.analysis_name, payload.output_folder)
    output_dir = os.path.join(CLIPS_DIR, analysis_folder)
    os.makedirs(output_dir, exist_ok=True)

    analysis_id = analysis_folder
    job_id = str(uuid.uuid4())
    body = payload.model_dump()
    body["youtube_url"] = youtube_url
    body["save_folder"] = _resolve_save_folder(body.get("save_folder"))
    create_job(job_id, analysis_id)
    if body.get("save_folder"):
        print("[AUTO SAVE PIPELINE ACTIVE]")
    asyncio.create_task(process_youtube_ingest_job(job_id, body, output_dir))
    return {"success": True, "job_id": job_id, "analysis_id": analysis_id, "status": "queued"}


@router.get("/ingest/status/{job_id}")
async def ingest_status(job_id: str):
    print(f"[FRONTEND REQUESTED JOB STATE] job_id={job_id}")
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return {k: job.get(k) for k in ["status", "progress", "step", "analysis_id", "clips", "error", "pipeline_event"]}


@router.get("/ingest/job/{job_id}")
async def ingest_job_state(job_id: str):
    print(f"[FRONTEND REQUESTED JOB STATE] job_id={job_id}")
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    print(f"[JOB RESTORED] job_id={job_id}")
    return {"job_id": job_id, **{k: job.get(k) for k in ["status", "progress", "step", "analysis_id", "clips", "finished", "error", "pipeline_event"]}}


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
                data = {k: payload.get(k) for k in ["status", "progress", "step", "analysis_id", "clips", "error", "pipeline_event"]}
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



def _clip_response_item(hook, index: int) -> dict:
    return {
        "id": f"clip-{index}",
        "label": f"Clip {index + 1}",
        "start": hook["start"],
        "end": hook["end"],
        "duration": round(hook["end"] - hook["start"], 2),
        "clip_path": _to_media_url(hook["clip_path"]),
        "raw_clip_path": _to_media_url(hook.get("raw_clip_path", hook["clip_path"])),
        "final_video": _to_media_url(hook["final_clip"]),
        "export_path": hook.get("export_path"),
        "local_export_path": hook.get("local_export_path"),
        "viral_score": hook["viral_score"],
        "hook_score": hook.get("hook_score", hook["viral_score"]),
        "retention_score": hook["retention_score"],
        "emotion_score": hook["emotional_score"],
        "title": hook.get("title_suggestion", ""),
        "caption": hook.get("caption_suggestion", ""),
        "description": hook.get("description_suggestion", ""),
        "hashtags": hook.get("hashtags", []),
        "emotion": hook.get("emotion", "Não analisado"),
        "category": hook.get("category", "Auto"),
        "viral_reason": hook.get("viral_reason", ""),
        "title_options": hook.get("title_options", []),
        "metadata_status": hook.get("metadata_status", "no_ai"),
        "metadata_provider": hook.get("metadata_provider", "none"),
    }


def _start_ai_metadata_background(hooks: list, next_state: dict, output_dir: str, provider: str | None = None) -> None:
    provider = provider or select_provider()
    limit = max_clips()
    if provider == "none" or limit <= 0 or not hooks:
        print(f"[AI_METADATA_FALLBACK_NO_AI] reason=background_disabled provider={provider} limit={limit}")
        return

    def _worker() -> None:
        print(f"[AI_METADATA_BACKGROUND_STARTED] provider={provider} max_clips={limit}")
        updated_hooks = list(hooks)
        for index, hook in enumerate(updated_hooks[:limit]):
            meta = generate_metadata(hook, index=index, output_dir=output_dir, provider=provider)
            updated_hooks[index] = apply_metadata_to_clip(hook, meta)
        refreshed = {**next_state, "clips": [_clip_response_item(hook, index) for index, hook in enumerate(updated_hooks)]}
        set_timeline_state(refreshed)
        save_timeline_state_for_analysis(refreshed.get("analysisId"), refreshed)
        print(f"[AI_METADATA_BACKGROUND_FINISHED] provider={provider} enriched={min(limit, len(updated_hooks))}")

    threading.Thread(target=_worker, name="ai-metadata-background", daemon=True).start()

def _build_upload_response(transcription, file_id: str, filepath: str, render_mode: str = "ai_tracking", video_quality: str = "1080p"):

    hooks = transcription["hooks"]
    duration = max([round(hook["end"] - hook["start"], 2) for hook in hooks], default=0.0)
    first_final_clip = hooks[0]["final_clip"] if hooks else filepath
    analysis_id = Path(hooks[0]["final_clip"]).parent.name if hooks else "default"

    is_waiting_dual_region = render_mode == "dual_region" and transcription.get("status") == "WAITING_FOR_DUAL_REGION_SETUP"
    status = "waiting_dual_region" if is_waiting_dual_region else "completed"
    print(f"[RENDER MODE SAVE] upload_response_render_mode={render_mode}")
    print("[DUAL REGION CONFIG SAVE] upload_response_dual_region_config=None")
    print(f"[TIMELINE STATE BOOTSTRAP] analysis_id={analysis_id}")
    selected_ai_provider = select_provider()
    pending_limit = max_clips() if selected_ai_provider != "none" else 0
    if pending_limit > 0:
        for index, hook in enumerate(hooks[:pending_limit]):
            hook["metadata_status"] = "pending"
            hook["metadata_provider"] = selected_ai_provider
    next_state = {
        "renderMode": "preview",
        "analysisId": analysis_id,
        "videoUrl": _to_media_url(first_final_clip),
        "previewVideoUrl": _to_media_url(first_final_clip),
        "exportVideoUrl": _to_media_url(first_final_clip),
        "duration": duration,
        "clips": [_clip_response_item(hook, index) for index, hook in enumerate(hooks)],

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
        "render_mode": render_mode,
        "status": status,
        "dual_regions": None,
        "dual_region_config": None,
        "video_quality": video_quality,
    }
    print(f"[TIMELINE STATE ANALYSIS] persisted_analysis_id={next_state.get('analysisId')}")
    set_timeline_state(next_state)
    save_timeline_state_for_analysis(next_state.get("analysisId"), next_state)
    _start_ai_metadata_background(hooks, next_state, Path(first_final_clip).parent.as_posix(), provider=selected_ai_provider)

    return {
        "success": True,
        "render_mode": render_mode,
        "analysis_id": analysis_id,
        "status": status,
        "video_quality": video_quality,
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
                "metadata_status": hook.get("metadata_status", "no_ai"),
                "metadata_provider": hook.get("metadata_provider", "none"),
                "clip_start": hook["start"],
                "clip_end": hook["end"],
                "emotional_score": hook["emotional_score"],
                "retention_score": hook["retention_score"],
                "duration": round(hook["end"] - hook["start"], 2),
                "final_clip": hook["final_clip"],
                "export_path": hook.get("export_path"),
                "local_export_path": hook.get("local_export_path"),
            }
            for hook in hooks
        ],
    }
