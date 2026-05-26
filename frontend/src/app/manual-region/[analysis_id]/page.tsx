'use client';

import { useEffect, useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { renderManualRegionFinal } from '@/lib/api';
import { useTimelineStore, type RegionBox } from '@/store/timelineStore';

const VIDEO_W = 1920;
const VIDEO_H = 1080;
const TARGET_ASPECT = 9 / 16;
const MIN_CROP_HEIGHT = 720;
const MIN_CROP_WIDTH = Math.round(MIN_CROP_HEIGHT * TARGET_ASPECT);
const SAFE_AREA_WIDTH_RATIO = 0.85;

const clamp = (v: number, min: number, max: number) => Math.min(Math.max(v, min), max);

const normalizeManualRegion = (region: RegionBox): RegionBox => {
  const maxHeight = VIDEO_H;
  const minHeight = clamp(MIN_CROP_HEIGHT, 1, VIDEO_H);
  const requestedHeight = clamp(region.height, minHeight, maxHeight);
  const widthFromAspect = Math.round(requestedHeight * TARGET_ASPECT);
  const maxWidth = Math.round(VIDEO_H * TARGET_ASPECT);
  const width = clamp(widthFromAspect, MIN_CROP_WIDTH, maxWidth);
  const height = Math.round(width / TARGET_ASPECT);

  return {
    width,
    height,
    x: clamp(region.x, 0, VIDEO_W - width),
    y: clamp(region.y, 0, VIDEO_H - height),
  };
};

type DragState =
  | { mode: 'move'; x: number; y: number; region: RegionBox }
  | { mode: 'resize'; x: number; y: number; region: RegionBox };

export default function ManualRegionPage() {
  const router = useRouter();
  const { analysis_id } = useParams<{ analysis_id: string }>();
  const { videoUrl, analysisId, hydrateFromBackend, manualRegion, setManualRegion, setClipRenderMode } = useTimelineStore();

  const playerRef = useRef<HTMLDivElement | null>(null);
  const isDraggingRef = useRef(false);
  const [dragState, setDragState] = useState<DragState | null>(null);

  const normalizedRegion = normalizeManualRegion(manualRegion);

  useEffect(() => {
    if (analysis_id && analysisId !== analysis_id) {
      if (isDraggingRef.current) {
        console.log('[MANUAL REGION HYDRATE BLOCKED]');
        return;
      }
      void hydrateFromBackend(analysis_id);
    }
    setClipRenderMode('manual_region');
  }, [analysis_id, analysisId, hydrateFromBackend, setClipRenderMode]);

  useEffect(() => {
    if (
      manualRegion.width !== normalizedRegion.width ||
      manualRegion.height !== normalizedRegion.height ||
      manualRegion.x !== normalizedRegion.x ||
      manualRegion.y !== normalizedRegion.y
    ) {
      setManualRegion(normalizedRegion, { persist: false });
    }
  }, [manualRegion, normalizedRegion, setManualRegion]);

  const startDrag = (e: React.PointerEvent, mode: DragState['mode']) => {
    e.preventDefault();
    e.stopPropagation();
    isDraggingRef.current = true;
    setDragState({ mode, x: e.clientX, y: e.clientY, region: normalizedRegion });
    console.log(`[MANUAL REGION ${mode === 'move' ? 'DRAG' : 'RESIZE'} START]`);
  };

  const onMove = (e: React.PointerEvent) => {
    if (!dragState || !playerRef.current) return;
    const rect = playerRef.current.getBoundingClientRect();
    const dxPx = (e.clientX - dragState.x) * (VIDEO_W / rect.width);

    if (dragState.mode === 'move') {
      const next = {
        ...normalizedRegion,
        x: clamp(dragState.region.x + dxPx, 0, VIDEO_W - normalizedRegion.width),
      };
      setManualRegion(next, { persist: false });
      return;
    }

    const maxHeight = VIDEO_H;
    const maxWidth = Math.round(maxHeight * TARGET_ASPECT);
    const requestedWidth = clamp(dragState.region.width + dxPx, MIN_CROP_WIDTH, maxWidth);
    const nextWidth = Math.round(requestedWidth);
    const nextHeight = Math.round(nextWidth / TARGET_ASPECT);

    const centeredX = clamp(dragState.region.x - (nextWidth - dragState.region.width) / 2, 0, VIDEO_W - nextWidth);
    const bottomAlignedY = VIDEO_H - nextHeight;

    setManualRegion(
      {
        x: centeredX,
        y: bottomAlignedY,
        width: nextWidth,
        height: nextHeight,
      },
      { persist: false },
    );
  };

  const onUp = () => {
    if (!dragState) return;
    setDragState(null);
    isDraggingRef.current = false;
    const finalRegion = normalizeManualRegion(useTimelineStore.getState().manualRegion);
    const aspectRatio = Number((finalRegion.width / finalRegion.height).toFixed(6));
    console.log('[MANUAL REGION DRAG END]');
    console.log('[MANUAL REGION FINAL]', {
      width: finalRegion.width,
      height: finalRegion.height,
      aspect_ratio: aspectRatio,
    });
    setManualRegion(finalRegion, { persist: true });
  };

  const confirm = async () => {
    const finalRegion = normalizeManualRegion(useTimelineStore.getState().manualRegion);
    const aspectRatio = finalRegion.width / finalRegion.height;
    if (Math.abs(aspectRatio - TARGET_ASPECT) > 0.002) {
      console.error('[MANUAL REGION FINAL INVALID ASPECT]', {
        width: finalRegion.width,
        height: finalRegion.height,
        aspect_ratio: aspectRatio,
      });
      throw new Error('Manual region must be 9:16 before render.');
    }

    console.log('[MANUAL REGION FINAL]', {
      width: finalRegion.width,
      height: finalRegion.height,
      aspect_ratio: Number(aspectRatio.toFixed(6)),
    });

    await renderManualRegionFinal({ analysis_id, render_mode: 'manual_region', manual_region: finalRegion });
    router.push(`/editor?analysis_id=${analysis_id}`);
  };

  return (
    <main className='min-h-screen bg-slate-950 p-6 text-white'>
      <div className='mx-auto max-w-5xl'>
        <h1 className='mb-3 text-3xl'>Manual Region Setup</h1>
        <div
          ref={playerRef}
          onPointerMove={onMove}
          onPointerUp={onUp}
          onPointerCancel={onUp}
          className='relative overflow-hidden rounded-xl border border-white/20'
        >
          {videoUrl ? <video src={videoUrl} className='aspect-video w-full object-cover' controls /> : <div className='grid aspect-video place-items-center'>Sem vídeo</div>}

          <div
            className='pointer-events-none absolute bg-black/55'
            style={{ inset: 0, clipPath: `polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%, 0% 0%, ${normalizedRegion.x / VIDEO_W * 100}% ${normalizedRegion.y / VIDEO_H * 100}%, ${((normalizedRegion.x + normalizedRegion.width) / VIDEO_W) * 100}% ${normalizedRegion.y / VIDEO_H * 100}%, ${((normalizedRegion.x + normalizedRegion.width) / VIDEO_W) * 100}% ${((normalizedRegion.y + normalizedRegion.height) / VIDEO_H) * 100}%, ${normalizedRegion.x / VIDEO_W * 100}% ${((normalizedRegion.y + normalizedRegion.height) / VIDEO_H) * 100}%, ${normalizedRegion.x / VIDEO_W * 100}% ${normalizedRegion.y / VIDEO_H * 100}%)` }}
          />

          <div
            onPointerDown={(e) => startDrag(e, 'move')}
            className='absolute cursor-grab border-2 border-cyan-300 bg-cyan-400/20 active:cursor-grabbing'
            style={{
              left: `${(normalizedRegion.x / VIDEO_W) * 100}%`,
              top: `${(normalizedRegion.y / VIDEO_H) * 100}%`,
              width: `${(normalizedRegion.width / VIDEO_W) * 100}%`,
              height: `${(normalizedRegion.height / VIDEO_H) * 100}%`,
            }}
          >
            <div className='pointer-events-none absolute left-1/2 top-0 h-full w-px -translate-x-1/2 bg-cyan-200/80' />
            <div
              className='pointer-events-none absolute left-1/2 top-0 h-full -translate-x-1/2 border-x border-dashed border-cyan-100/80'
              style={{ width: `${SAFE_AREA_WIDTH_RATIO * 100}%` }}
            />
            <button
              type='button'
              aria-label='Resize 9:16 region'
              onPointerDown={(e) => startDrag(e, 'resize')}
              className='absolute -right-3 bottom-3 h-6 w-6 rounded-full border border-cyan-100 bg-cyan-300 text-black shadow-lg'
            >
              ↔
            </button>
          </div>
        </div>

        <button onClick={confirm} className='mt-4 rounded-lg bg-cyan-400 px-4 py-2 font-semibold text-black'>
          Confirmar Manual Region
        </button>
      </div>
    </main>
  );
}
