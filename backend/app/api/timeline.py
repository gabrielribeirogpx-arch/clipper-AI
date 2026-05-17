from fastapi import APIRouter
from app.data.timeline_state import get_timeline_state, set_timeline_state
from app.schemas.timeline import TimelineUpdateRequest

router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get("/render-state")
def get_render_state():
    return get_timeline_state()


@router.get("/b-roll")
def get_broll():
    return get_timeline_state().get("broll", [])


@router.put("/update")
def update_timeline(payload: TimelineUpdateRequest):
    current_state = get_timeline_state()
    current_state["broll"] = [item.model_dump() for item in payload.broll]
    current_state["hooks"] = [item.model_dump() for item in payload.hooks]
    current_state["cuts"] = [item.model_dump() for item in payload.cuts]
    if payload.render_mode:
        current_state["render_mode"] = payload.render_mode
    if payload.dual_regions:
        current_state["dual_regions"] = payload.dual_regions.model_dump()
    set_timeline_state(current_state)

    return {"status": "updated"}
