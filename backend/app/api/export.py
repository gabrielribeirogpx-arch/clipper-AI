from __future__ import annotations

import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.data.timeline_state import get_timeline_state, set_timeline_state
from app.services.render_quality import (
    EXPORT_AUDIO_BITRATE,
    EXPORT_AUDIO_CODEC,
    EXPORT_CRF,
    EXPORT_MOVFLAGS,
    EXPORT_PIXEL_FORMAT,
    EXPORT_PRESET,
    EXPORT_VIDEO_CODEC,
    VERTICAL_PREMIUM_FILTER,
)

router = APIRouter(tags=["export"])

BASE_DIR = Path(__file__).resolve().parents[1]
CLIPS_ROOT = (BASE_DIR / "clips").resolve()
EXPORTS_ROOT = (BASE_DIR / "exports").resolve()


class ExportRequest(dict):
    pass


def _run_ffmpeg_export(input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vf",
        VERTICAL_PREMIUM_FILTER,
        "-c:v",
        EXPORT_VIDEO_CODEC,
        "-preset",
        EXPORT_PRESET,
        "-crf",
        str(EXPORT_CRF),
        "-pix_fmt",
        EXPORT_PIXEL_FORMAT,
        "-c:a",
        EXPORT_AUDIO_CODEC,
        "-b:a",
        EXPORT_AUDIO_BITRATE,
        "-movflags",
        EXPORT_MOVFLAGS,
        str(output_path),
    ]
    print("[RENDER QUALITY PROFILE] profile=final_export")
    print(f"[FFMPEG START] profile=final_export command={' '.join(command)}")
    proc = subprocess.run(command, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        print(f"[FFMPEG ERROR] profile=final_export output={output_path} stderr={proc.stderr}")
        raise RuntimeError(proc.stderr or "ffmpeg export failed")
    print(f"[FFMPEG SUCCESS] profile=final_export output={output_path}")


@router.post("/export")
def export_clip(payload: dict):
    clip_id = payload.get("clip_id")
    if not clip_id:
        raise HTTPException(status_code=400, detail="clip_id is required")

    state = get_timeline_state()
    clips = state.get("clips", [])
    clip = next((item for item in clips if item.get("id") == clip_id), None)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    source_media = clip.get("export_video") or clip.get("preview_video") or clip.get("clip_path")
    if not source_media:
        raise HTTPException(status_code=400, detail="Clip has no source media")

    rel_source = Path(str(source_media).replace("/media/", "", 1))
    source_path = (CLIPS_ROOT / rel_source).resolve()
    try:
        source_path.relative_to(CLIPS_ROOT)
    except ValueError as error:
        raise HTTPException(status_code=403, detail="Invalid source path") from error

    if not source_path.exists():
        raise HTTPException(status_code=404, detail="Source media not found")

    analysis_id = rel_source.parts[0] if len(rel_source.parts) > 1 else "default"
    clip_name = source_path.stem
    final_name = f"{clip_name}.mp4"
    export_path = (EXPORTS_ROOT / analysis_id / final_name).resolve()

    print(f"[EXPORT START] clip_id={clip_id} source={source_path} output={export_path}")
    try:
        _run_ffmpeg_export(source_path, export_path)
    except Exception as error:
        print(f"[EXPORT ERROR] clip_id={clip_id} error={error}")
        raise HTTPException(status_code=500, detail=f"Export failed: {error}") from error

    export_media_path = Path("/media") / Path("exports") / analysis_id / final_name
    state["renderMode"] = "export"
    state["exportVideoUrl"] = export_media_path.as_posix()
    state["videoUrl"] = export_media_path.as_posix()
    state["previewVideoUrl"] = export_media_path.as_posix()
    set_timeline_state(state)

    print(f"[EXPORT SUCCESS] clip_id={clip_id} output={export_path}")
    return {
        "success": True,
        "export_path": str(export_path),
        "download_url": export_media_path.as_posix(),
    }
