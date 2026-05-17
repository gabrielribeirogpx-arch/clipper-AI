from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from threading import Lock
from typing import Any

INGEST_JOBS: dict[str, dict[str, Any]] = {}
INGEST_EVENTS: dict[str, list[asyncio.Queue[dict[str, Any]]]] = {}
_LOCK = Lock()
JOB_RETENTION_SECONDS = 3600


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_job(job_id: str, analysis_id: str) -> None:
    now = _now_iso()
    with _LOCK:
        INGEST_JOBS[job_id] = {
            "status": "queued",
            "progress": 0,
            "step": "Job queued",
            "analysis_id": analysis_id,
            "clips": [],
            "finished": False,
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
    print(f"[JOB REGISTERED] job_id={job_id} analysis_id={analysis_id}")


def get_job(job_id: str) -> dict[str, Any] | None:
    with _LOCK:
        job = INGEST_JOBS.get(job_id)
        return dict(job) if job else None


def update_job(job_id: str, **fields: Any) -> dict[str, Any] | None:
    with _LOCK:
        job = INGEST_JOBS.get(job_id)
        if not job:
            return None
        job.update(fields)
        if fields.get("status") in {"completed", "failed"}:
            job["finished"] = True
        job["updated_at"] = _now_iso()
        snapshot = dict(job)
    print(f"[JOB STATUS UPDATE] job_id={job_id} status={snapshot.get('status')} progress={snapshot.get('progress')} step={snapshot.get('step')}")
    _broadcast(job_id, snapshot)
    return snapshot


def register_listener(job_id: str) -> asyncio.Queue[dict[str, Any]]:
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    with _LOCK:
        INGEST_EVENTS.setdefault(job_id, []).append(queue)
        snapshot = dict(INGEST_JOBS.get(job_id, {}))
    if snapshot:
        print(f"[JOB RECOVERED] job_id={job_id}")
        queue.put_nowait(snapshot)
    return queue


def unregister_listener(job_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
    with _LOCK:
        listeners = INGEST_EVENTS.get(job_id, [])
        if queue in listeners:
            listeners.remove(queue)
        if not listeners:
            INGEST_EVENTS.pop(job_id, None)


def _broadcast(job_id: str, snapshot: dict[str, Any]) -> None:
    with _LOCK:
        listeners = list(INGEST_EVENTS.get(job_id, []))
    for q in listeners:
        q.put_nowait(snapshot)


def cleanup_jobs() -> int:
    now = datetime.now(timezone.utc)
    removed = 0
    with _LOCK:
        for job_id in list(INGEST_JOBS.keys()):
            job = INGEST_JOBS[job_id]
            if not job.get("finished"):
                continue
            updated_at = datetime.fromisoformat(job.get("updated_at", _now_iso()))
            age_seconds = (now - updated_at).total_seconds()
            if age_seconds > JOB_RETENTION_SECONDS:
                INGEST_JOBS.pop(job_id, None)
                INGEST_EVENTS.pop(job_id, None)
                removed += 1
    if removed:
        print(f"[JOB CLEANUP] removed={removed}")
    return removed
