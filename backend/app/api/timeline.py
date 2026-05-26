from pathlib import Path
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from app.data.timeline_state import (
    get_timeline_state,
    set_timeline_state,
    get_timeline_state_for_analysis,
    save_timeline_state_for_analysis,
)
from app.schemas.timeline import TimelineUpdateRequest
from app.services.vertical_render_service import render_dual_region_clip, render_semi_auto_vertical

router = APIRouter(prefix="/timeline", tags=["timeline"])

class DualRegionRenderRequest(BaseModel):
    analysis_id: str
    render_mode: str
    dual_region_config: dict

class SemiAutoRenderRequest(BaseModel):
    analysis_id: str
    render_mode: str


def _to_filesystem_path(media_url: str) -> Path:
    if not media_url.startswith('/media/'):
        raise HTTPException(status_code=400, detail=f'invalid media path: {media_url}')
    return Path('app/clips') / media_url.replace('/media/', '', 1)


def _to_media_url(path: Path) -> str:
    rel_path = path.as_posix().replace('app/clips/', '', 1)
    return f"/media/{rel_path}"


@router.get("/render-state")
def get_render_state(analysis_id: str | None = Query(default=None)):
    if analysis_id:
        normalized_analysis_id = str(analysis_id)
        print(f"[EDITOR HYDRATION REQUEST] analysis_id={normalized_analysis_id}")
        analysis_state = get_timeline_state_for_analysis(normalized_analysis_id)
        if analysis_state:
            set_timeline_state(analysis_state)
            state = analysis_state
            print(f"[EDITOR HYDRATION HIT] analysis_id={normalized_analysis_id}")
        else:
            print(f"[EDITOR HYDRATION MISS] analysis_id={normalized_analysis_id}")
            raise HTTPException(status_code=404, detail=f"timeline state not found for analysis_id={normalized_analysis_id}")
    else:
        state = get_timeline_state()
    print(f"[RENDER MODE LOAD] render_mode={state.get('render_mode')}")
    print(f"[DUAL REGION CONFIG LOAD] dual_region_config={state.get('dual_region_config')}")
    state["semi_auto_config"] = state.get("semi_auto_config", state.get("semi_auto"))
    print(f"[TIMELINE LOAD SEMI AUTO] semi_auto_config={state.get('semi_auto_config')}")
    return state


@router.get("/b-roll")
def get_broll():
    return get_timeline_state().get("broll", [])


@router.put("/update")
def update_timeline(payload: TimelineUpdateRequest):
    if payload.render_mode in {f"manual_{'region'}", f"manual-{'region'}", f"manual{'Region'}"}:
        print("[LEGACY MANUAL REGION DETECTED] source=timeline_update")
        raise HTTPException(status_code=400, detail="legacy manual render_mode is not supported")
    print(f"[RENDER MODE SAVE] incoming_render_mode={payload.render_mode}")
    print(f"[DUAL REGION CONFIG SAVE] incoming_dual_regions={payload.dual_regions.model_dump() if payload.dual_regions else None}")
    resolved_semi_auto = payload.semi_auto_config or payload.semi_auto
    current_state = get_timeline_state()
    print(f"[TIMELINE BEFORE SAVE] {current_state.get('render_mode')}")
    print(f"[TIMELINE ASSIGNED] {payload.render_mode}")
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
    if resolved_semi_auto is not None:
        semi_auto_dump = resolved_semi_auto.model_dump()
        current_state["semi_auto"] = semi_auto_dump
        current_state["semi_auto_config"] = semi_auto_dump
        print(f"[TIMELINE SAVE SEMI AUTO] semi_auto_config={semi_auto_dump}")
    set_timeline_state(current_state)
    normalized_analysis_id = str(current_state.get("analysisId")) if current_state.get("analysisId") is not None else None
    save_timeline_state_for_analysis(normalized_analysis_id, current_state)
    persisted_state = get_timeline_state_for_analysis(normalized_analysis_id) or {}
    print("[PERSISTENCE VERIFY]", {
        "analysis_id": normalized_analysis_id,
        "render_mode": persisted_state.get("render_mode"),
        "dual_region_config": persisted_state.get("dual_region_config"),
        "semi_auto_config": persisted_state.get("semi_auto_config", persisted_state.get("semi_auto")),
    })
    print(f"[TIMELINE AFTER COMMIT] {current_state.get('render_mode')}")
    print(f"[RENDER MODE SAVE] persisted_render_mode={current_state.get('render_mode')}")
    print(f"[DUAL REGION CONFIG SAVE] persisted_dual_region_config={current_state.get('dual_region_config')}")

    return {"status": "updated"}


@router.post('/render-dual-region')
def render_dual_region_final(payload: DualRegionRenderRequest):
    print('[DUAL REGION MANUAL RENDER START]')
    if payload.render_mode != 'dual_region':
        raise HTTPException(status_code=400, detail='render_mode must be dual_region')
    if not payload.dual_region_config:
        print('[DUAL REGION CONFIG MISSING] analysis_id={} dual_region_config=None'.format(payload.analysis_id))
        print('[DUAL REGION RENDER BLOCKED] reason=missing_payload_dual_region_config')
        raise HTTPException(status_code=400, detail='dual_region_config is required for dual_region render')
    print(f"[DUAL REGION CONFIG RECEIVED] analysis_id={payload.analysis_id} regionA={payload.dual_region_config.get('regionA')} regionB={payload.dual_region_config.get('regionB')}")

    state = get_timeline_state()
    print(f"[TIMELINE STATE BEFORE FINAL RENDER] analysisId={state.get('analysisId')} clips={len(state.get('clips', []))}")
    print(f"[FINAL RENDER PAYLOAD ANALYSIS] analysis_id={payload.analysis_id}")
    backend_analysis_id = state.get('analysisId')
    print(f"[TIMELINE STATE ANALYSIS] timeline_state.analysisId={backend_analysis_id}")

    if backend_analysis_id != payload.analysis_id:
        print(f"[TIMELINE FALLBACK LOAD] reason=analysis_mismatch expected={payload.analysis_id} actual={backend_analysis_id}")
        recovered = get_timeline_state_for_analysis(payload.analysis_id)
        if recovered:
            state = recovered
            set_timeline_state(state)
            backend_analysis_id = state.get('analysisId')
            print(f"[TIMELINE STATE RECOVERED] analysisId={backend_analysis_id} clips={len(state.get('clips', []))}")

    if backend_analysis_id != payload.analysis_id:
        print(f"[TIMELINE INTERNAL 404] reason=analysis_not_found payload_analysis_id={payload.analysis_id} timeline_state_analysis_id={backend_analysis_id}")
        raise HTTPException(status_code=404, detail='analysis not found in timeline state')

    clips = state.get('clips', [])
    print(f"[DUAL REGION RAW CLIPS LOADED] count={len(clips)}")
    print('[DUAL REGION FINAL RENDER START]')

    updated_clips = []
    for index, clip in enumerate(clips):
        raw_clip_path = _to_filesystem_path(clip.get('raw_clip_path') or clip.get('clip_path'))
        if not raw_clip_path.exists():
            raise HTTPException(status_code=404, detail=f'raw clip missing: {raw_clip_path.as_posix()}')

        dual_clip_path = raw_clip_path.with_name(f"clip_{index}_dual.mp4")
        render_dual_region_clip(str(raw_clip_path), str(dual_clip_path), payload.dual_region_config)

        updated = {**clip}
        updated['clip_path'] = _to_media_url(dual_clip_path)
        updated['final_video'] = _to_media_url(dual_clip_path)
        updated_clips.append(updated)

    state['clips'] = updated_clips
    state['render_mode'] = 'dual_region'
    state['dual_regions'] = payload.dual_region_config
    state['dual_region_config'] = payload.dual_region_config
    print(f"[DUAL REGION CONFIG SAVED] analysis_id={payload.analysis_id} regionA={payload.dual_region_config.get('regionA')} regionB={payload.dual_region_config.get('regionB')}")
    if updated_clips:
        state['videoUrl'] = updated_clips[0]['final_video']
        state['previewVideoUrl'] = updated_clips[0]['final_video']
        state['exportVideoUrl'] = updated_clips[0]['final_video']

    set_timeline_state(state)
    save_timeline_state_for_analysis(state.get("analysisId"), state)
    print('[DUAL REGION FINAL RENDER COMPLETE]')
    print('[EDITOR CLIPS REPLACED]')
    return {'status': 'rendered', 'clips': updated_clips, 'analysis_id': payload.analysis_id}

@router.post('/render-semi-auto')
def render_semi_auto_final(payload: SemiAutoRenderRequest):
    print('[RENDER PIPELINE SEMI AUTO]')
    if payload.render_mode != 'semi_auto':
        raise HTTPException(status_code=400, detail='render_mode must be semi_auto')
    state = get_timeline_state()
    clips = state.get('clips', [])
    updated_clips = []
    for index, clip in enumerate(clips):
        raw_clip_path = _to_filesystem_path(clip.get('raw_clip_path') or clip.get('clip_path'))
        semi_auto_clip_path = raw_clip_path.with_name(f"clip_{index}_semi_auto.mp4")
        render_semi_auto_vertical(str(raw_clip_path), str(semi_auto_clip_path))
        updated = {**clip}
        updated['clip_path'] = _to_media_url(semi_auto_clip_path)
        updated['final_video'] = _to_media_url(semi_auto_clip_path)
        updated_clips.append(updated)
    state['clips'] = updated_clips
    state['render_mode'] = 'semi_auto'
    set_timeline_state(state)
    save_timeline_state_for_analysis(state.get("analysisId"), state)
    return {'status': 'rendered', 'clips': updated_clips, 'analysis_id': payload.analysis_id}



@router.get("/debug-routes")
def debug_timeline_routes():
    return [
        {
            "path": route.path,
            "methods": sorted(list(getattr(route, "methods", []) or [])),
            "name": route.name,
        }
        for route in router.routes
        if "timeline" in route.path
    ]
