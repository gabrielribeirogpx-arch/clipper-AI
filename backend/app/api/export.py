from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.data.timeline_state import get_timeline_state, set_timeline_state

router = APIRouter(tags=["export"])

BASE_DIR = Path(__file__).resolve().parents[1]
CLIPS_ROOT = (BASE_DIR / "clips").resolve()
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

    source_media = clip.get("final_video") or clip.get("export_video") or clip.get("preview_video") or clip.get("clip_path")
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

    export_media_path = Path("/media") / rel_source
    print(f"[PREVIEW SOURCE] clip_id={clip_id} source={source_path}")
    print(f"[EXPORT SOURCE] clip_id={clip_id} source={source_path}")
    print(f"[FINAL CLIP SOURCE] clip_id={clip_id} source={source_path}")
    state["renderMode"] = "export"
    state["exportVideoUrl"] = export_media_path.as_posix()
    state["videoUrl"] = export_media_path.as_posix()
    state["previewVideoUrl"] = export_media_path.as_posix()
    set_timeline_state(state)

    print(f"[EXPORT SUCCESS] clip_id={clip_id} output={source_path}")
    return {
        "success": True,
        "export_path": str(source_path),
        "download_url": export_media_path.as_posix(),
    }
