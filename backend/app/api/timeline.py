from fastapi import APIRouter, Query
from app.data.timeline_state import get_timeline_state, set_timeline_state
from app.schemas.timeline import TimelineUpdateRequest

router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get("/render-state")
def get_render_state(analysis_id: str | None = Query(default=None)):
    if analysis_id:
        print(f"[EDITOR HYDRATION REQUEST] analysis_id={analysis_id}")
    state = get_timeline_state()
    print(f"[RENDER MODE LOAD] render_mode={state.get('render_mode')}")
    print(f"[DUAL REGION CONFIG LOAD] dual_region_config={state.get('dual_region_config')}")
    return state


@router.get("/b-roll")
def get_broll():
    return get_timeline_state().get("broll", [])


@router.put("/update")
def update_timeline(payload: TimelineUpdateRequest):
    print(f"[RENDER MODE SAVE] incoming_render_mode={payload.render_mode}")
    print(f"[DUAL REGION CONFIG SAVE] incoming_dual_regions={payload.dual_regions.model_dump() if payload.dual_regions else None}")
    current_state = get_timeline_state()
    current_state["broll"] = [item.model_dump() for item in payload.broll]
    current_state["hooks"] = [item.model_dump() for item in payload.hooks]
    current_state["cuts"] = [item.model_dump() for item in payload.cuts]
    if payload.render_mode:
        current_state["render_mode"] = payload.render_mode
    else:
        print(f"[RENDER MODE FALLBACK] keeping_existing_render_mode={current_state.get('render_mode')}")
    if payload.dual_regions:
        current_state["dual_regions"] = payload.dual_regions.model_dump()
        current_state["dual_region_config"] = payload.dual_regions.model_dump()
    set_timeline_state(current_state)
    print(f"[RENDER MODE SAVE] persisted_render_mode={current_state.get('render_mode')}")
    print(f"[DUAL REGION CONFIG SAVE] persisted_dual_region_config={current_state.get('dual_region_config')}")

    return {"status": "updated"}
