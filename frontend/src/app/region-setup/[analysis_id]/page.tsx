'use client';

import { useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { useTimelineStore, type RegionBox } from '@/store/timelineStore';

type RegionKey = 'regionA' | 'regionB';

type ActiveDrag = {
  pointerId: number;
  key: RegionKey;
  type: 'move' | 'resize';
  handle?: ResizeHandle;
  startX: number;
  startY: number;
  origin: RegionBox;
};
type ResizeHandle = 'n' | 's' | 'e' | 'w' | 'ne' | 'nw' | 'se' | 'sw';

const VIDEO_W = 1920;
const VIDEO_H = 1080;
const MIN_REGION_W = 220;
const MIN_REGION_H = 220;

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

export default function RegionSetupPage() {
  const router = useRouter();
  const { videoUrl, dualRegions, setDualRegions, generatedClips, analysisId, clipRenderMode } = useTimelineStore();
  const playerRef = useRef<HTMLDivElement | null>(null);
  const [activeDrag, setActiveDrag] = useState<ActiveDrag | null>(null);
  const [selectedRegion, setSelectedRegion] = useState<RegionKey>('regionA');
  const [showGrid, setShowGrid] = useState(true);

  const presets = {
    podcast: { regionA: { x: 120, y: 80, width: 1680, height: 460 }, regionB: { x: 120, y: 540, width: 1680, height: 460 } },
    gameplay: { regionA: { x: 80, y: 120, width: 700, height: 880 }, regionB: { x: 860, y: 80, width: 980, height: 920 } },
    debate: { regionA: { x: 80, y: 100, width: 840, height: 900 }, regionB: { x: 1000, y: 100, width: 840, height: 900 } },
    reaction: { regionA: { x: 120, y: 120, width: 1020, height: 860 }, regionB: { x: 1140, y: 170, width: 660, height: 760 } },
  } as const;

  const startDrag = (e: React.PointerEvent, key: RegionKey, type: 'move' | 'resize', handle?: ResizeHandle) => {
    if (clipRenderMode !== 'dual_region') return;
    e.preventDefault();
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    setSelectedRegion(key);
    if (type === 'move') {
      console.log('[DUAL REGION DRAG START]', { key, x: e.clientX, y: e.clientY });
    } else {
      console.log('[DUAL REGION RESIZE START]', { key, handle, x: e.clientX, y: e.clientY });
    }
    setActiveDrag({ pointerId: e.pointerId, key, type, handle, startX: e.clientX, startY: e.clientY, origin: dualRegions[key] });
  };

  const onPointerMove = (e: React.PointerEvent) => {
    if (!activeDrag || !playerRef.current || e.pointerId !== activeDrag.pointerId) return;

    const rect = playerRef.current.getBoundingClientRect();
    const scaleX = VIDEO_W / rect.width;
    const scaleY = VIDEO_H / rect.height;
    const dx = (e.clientX - activeDrag.startX) * scaleX;
    const dy = (e.clientY - activeDrag.startY) * scaleY;

    const next = { ...dualRegions };
    const current = next[activeDrag.key];

    if (activeDrag.type === 'move') {
      current.x = clamp(activeDrag.origin.x + dx, 0, VIDEO_W - activeDrag.origin.width);
      current.y = clamp(activeDrag.origin.y + dy, 0, VIDEO_H - activeDrag.origin.height);
      console.log('[DUAL REGION DRAG MOVE]', activeDrag.key, current);
    } else {
      let nextX = activeDrag.origin.x;
      let nextY = activeDrag.origin.y;
      let nextW = activeDrag.origin.width;
      let nextH = activeDrag.origin.height;
      const handle = activeDrag.handle ?? 'se';

      if (handle.includes('e')) nextW = activeDrag.origin.width + dx;
      if (handle.includes('s')) nextH = activeDrag.origin.height + dy;
      if (handle.includes('w')) {
        nextW = activeDrag.origin.width - dx;
        nextX = activeDrag.origin.x + dx;
      }
      if (handle.includes('n')) {
        nextH = activeDrag.origin.height - dy;
        nextY = activeDrag.origin.y + dy;
      }

      const maxWidthByX = VIDEO_W - nextX;
      const maxHeightByY = VIDEO_H - nextY;
      nextW = clamp(nextW, MIN_REGION_W, maxWidthByX);
      nextH = clamp(nextH, MIN_REGION_H, maxHeightByY);

      nextX = clamp(nextX, 0, VIDEO_W - MIN_REGION_W);
      nextY = clamp(nextY, 0, VIDEO_H - MIN_REGION_H);
      nextW = clamp(nextW, MIN_REGION_W, VIDEO_W - nextX);
      nextH = clamp(nextH, MIN_REGION_H, VIDEO_H - nextY);

      current.x = nextX;
      current.y = nextY;
      current.width = nextW;
      current.height = nextH;
      console.log('[DUAL REGION RESIZE MOVE]', activeDrag.key, { handle, ...current });
    }

    setDualRegions(next);
  };

  const endDrag = (e: React.PointerEvent) => {
    if (!activeDrag || e.pointerId !== activeDrag.pointerId) return;
    const target = e.target as HTMLElement;
    if (target?.hasPointerCapture?.(e.pointerId)) {
      target.releasePointerCapture(e.pointerId);
    }
    if (activeDrag.type === 'move') {
      console.log('[DUAL REGION DRAG END]', { key: activeDrag.key, region: dualRegions[activeDrag.key] });
    } else {
      console.log('[DUAL REGION RESIZE END]', { key: activeDrag.key, handle: activeDrag.handle, region: dualRegions[activeDrag.key] });
    }
    setActiveDrag(null);
  };

  const toPercent = (value: number, base: number) => `${(value / base) * 100}%`;

  const confirmRegions = () => {
    console.log('[DUAL REGION CONFIRMED]', dualRegions);
    setDualRegions(dualRegions);
    const target = generatedClips.length > 0 ? '/editor' : '/editor';
    const query = analysisId ? `?analysis_id=${analysisId}` : '';
    router.push(`${target}${query}`);
  };

  const containerStyles = useMemo(() => ({
    regionA: 'border-cyan-300/90 bg-cyan-400/15 shadow-[0_0_20px_rgba(34,211,238,0.55)]',
    regionB: 'border-fuchsia-300/90 bg-fuchsia-500/15 shadow-[0_0_20px_rgba(232,121,249,0.55)]',
  }), []);

  return (
    <main className='min-h-screen bg-gradient-to-br from-slate-950 via-black to-slate-900 p-6 text-white'>
      <div className='mx-auto max-w-6xl'>
        <h1 className='mb-1 text-3xl font-semibold tracking-tight'>Dual Region Setup</h1>
        <p className='mb-6 text-sm text-slate-300'>Defina as áreas de captura para o render final vertical 9:16.</p>

        <div
          className='relative overflow-hidden rounded-2xl border border-white/20 bg-black/40 backdrop-blur'
          onPointerMove={onPointerMove}
          onPointerUp={endDrag}
          onPointerCancel={endDrag}
          ref={playerRef}
        >
          {videoUrl ? <video src={videoUrl} className='aspect-video w-full object-cover' controls /> : <div className='grid aspect-video place-items-center'>Sem vídeo de origem</div>}

          {showGrid && <div className='pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.09)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.09)_1px,transparent_1px)] bg-[size:8%_10%]' />}
          <div className='pointer-events-none absolute inset-x-0 top-1/2 h-px bg-white/35' />

          {(['regionA', 'regionB'] as const).map((key) => {
            const region = dualRegions[key];
            return (
              <motion.div
                key={key}
                layout
                transition={{ type: 'spring', stiffness: 400, damping: 35 }}
                className={`absolute cursor-move rounded-xl border-2 transition-[box-shadow,transform] duration-100 ease-out touch-none ${containerStyles[key]} ${selectedRegion === key || activeDrag?.key === key ? 'ring-2 ring-white/70 shadow-[0_0_0_1px_rgba(255,255,255,0.45),0_0_30px_rgba(255,255,255,0.35)]' : 'hover:shadow-[0_0_18px_rgba(255,255,255,0.2)]'}`}
                style={{
                  left: toPercent(region.x, VIDEO_W),
                  top: toPercent(region.y, VIDEO_H),
                  width: toPercent(region.width, VIDEO_W),
                  height: toPercent(region.height, VIDEO_H),
                }}
                onPointerDown={(e) => startDrag(e, key, 'move')}
              >
                <div className='absolute left-2 top-2 rounded-md bg-black/65 px-2 py-1 text-xs font-semibold tracking-wider'>
                  {key === 'regionA' ? 'REGIÃO A' : 'REGIÃO B'}
                </div>
                {([
                  { h: 'n', cls: 'top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 cursor-n-resize w-5 h-2' },
                  { h: 's', cls: 'bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 cursor-s-resize w-5 h-2' },
                  { h: 'e', cls: 'right-0 top-1/2 translate-x-1/2 -translate-y-1/2 cursor-e-resize w-2 h-5' },
                  { h: 'w', cls: 'left-0 top-1/2 -translate-x-1/2 -translate-y-1/2 cursor-w-resize w-2 h-5' },
                  { h: 'ne', cls: 'right-0 top-0 translate-x-1/2 -translate-y-1/2 cursor-ne-resize w-3 h-3' },
                  { h: 'nw', cls: 'left-0 top-0 -translate-x-1/2 -translate-y-1/2 cursor-nw-resize w-3 h-3' },
                  { h: 'se', cls: 'right-0 bottom-0 translate-x-1/2 translate-y-1/2 cursor-se-resize w-3 h-3' },
                  { h: 'sw', cls: 'left-0 bottom-0 -translate-x-1/2 translate-y-1/2 cursor-sw-resize w-3 h-3' },
                ] as { h: ResizeHandle; cls: string }[]).map(({ h, cls }) => (
                  <button
                    key={`${key}-${h}`}
                    type='button'
                    aria-label={`Resize ${key} ${h}`}
                    className={`absolute rounded-md border border-white/80 bg-white/85 shadow-[0_0_12px_rgba(255,255,255,0.9)] ${cls}`}
                    onPointerDown={(e) => {
                      e.stopPropagation();
                      startDrag(e, key, 'resize', h);
                    }}
                  />
                ))}
              </motion.div>
            );
          })}
        </div>

        <div className='mt-4 flex flex-wrap gap-2'>
          {Object.entries(presets).map(([k, value]) => (
            <button key={k} className='rounded-lg border border-white/20 bg-slate-800/80 px-3 py-2 text-sm hover:bg-slate-700' onClick={() => setDualRegions(value)}>{k}</button>
          ))}
          <button className='rounded-lg border border-cyan-300/50 bg-cyan-400/10 px-3 py-2 text-sm hover:bg-cyan-300/20' onClick={() => setShowGrid((prev) => !prev)}>{showGrid ? 'Ocultar grid' : 'Mostrar grid'}</button>
        </div>

        <section className='mt-8'>
          <h2 className='mb-3 text-lg font-medium'>Preview vertical 9:16 (tempo real)</h2>
          <div className='w-[310px] overflow-hidden rounded-2xl border border-white/20 bg-black shadow-2xl'>
            <div className='relative mx-auto aspect-[9/16] w-full'>
              <video src={videoUrl ?? ''} className='absolute inset-0 h-full w-full object-cover' muted playsInline />
              <div className='absolute inset-x-0 top-0 h-1/2 overflow-hidden border-b border-white/30'>
                <video
                  src={videoUrl ?? ''}
                  className='absolute max-w-none'
                  style={{
                    left: `-${(dualRegions.regionA.x / dualRegions.regionA.width) * 100}%`,
                    top: `-${(dualRegions.regionA.y / dualRegions.regionA.height) * 100}%`,
                    width: `${(VIDEO_W / dualRegions.regionA.width) * 100}%`,
                    height: `${(VIDEO_H / dualRegions.regionA.height) * 100}%`,
                  }}
                  muted
                  playsInline
                />
              </div>
              <div className='absolute inset-x-0 bottom-0 h-1/2 overflow-hidden'>
                <video
                  src={videoUrl ?? ''}
                  className='absolute max-w-none'
                  style={{
                    left: `-${(dualRegions.regionB.x / dualRegions.regionB.width) * 100}%`,
                    top: `-${(dualRegions.regionB.y / dualRegions.regionB.height) * 100}%`,
                    width: `${(VIDEO_W / dualRegions.regionB.width) * 100}%`,
                    height: `${(VIDEO_H / dualRegions.regionB.height) * 100}%`,
                  }}
                  muted
                  playsInline
                />
              </div>
              <div className='pointer-events-none absolute inset-x-0 top-1/2 h-px bg-white/60' />
            </div>
          </div>
        </section>

        <button
          className='mt-8 rounded-xl bg-cyan-400 px-5 py-3 font-semibold text-black transition hover:bg-cyan-300'
          onClick={confirmRegions}
        >
          Confirmar Regiões
        </button>
      </div>
    </main>
  );
}
