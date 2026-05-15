from fastapi import APIRouter
from app.data.mock_timeline import render_state, subtitles, broll, hooks
from app.schemas.timeline import TimelineUpdateRequest

router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get("/render-state")
def get_render_state():
    return render_state


@router.get("/subtitles")
def get_subtitles():
    return subtitles


@router.get("/b-roll")
def get_broll():
    return broll


@router.put("/update")
def update_timeline(payload: TimelineUpdateRequest):
    subtitles.clear()
    subtitles.extend([item.model_dump() for item in payload.subtitles])

    broll.clear()
    broll.extend([item.model_dump() for item in payload.broll])

    hooks.clear()
    hooks.extend([item.model_dump() for item in payload.hooks])

    render_state["cuts"] = [item.model_dump() for item in payload.cuts]

    return {"status": "updated"}
