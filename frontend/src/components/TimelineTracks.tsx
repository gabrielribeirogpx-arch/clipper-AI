'use client';

import { memo, useMemo, useRef } from 'react';
import { useMounted } from '@/hooks/useMounted';
import { motion } from 'framer-motion';
import { pixelsToSeconds, secondsToPixels } from '@/lib/timelineEngine';
import { TrackType, useTimelineStore } from '@/store/timelineStore';

const trackStyles: Record<TrackType, string> = {
  subtitles: 'from-cyan-500/85 to-cyan-300/70 border-cyan-200/60 shadow-[0_0_24px_rgba(34,211,238,.25)]',
  broll: 'from-violet-500/85 to-purple-300/70 border-violet-200/60 shadow-[0_0_24px_rgba(168,85,247,.28)]',
  hooks: 'from-rose-500/88 to-orange-400/72 border-rose-200/60 shadow-[0_0_24px_rgba(251,113,133,.28)]',
  cuts: 'from-amber-500/85 to-yellow-300/70 border-amber-200/60 shadow-[0_0_24px_rgba(251,191,36,.28)]',
  effects: 'from-fuchsia-500/85 to-purple-300/70 border-fuchsia-200/60 shadow-[0_0_24px_rgba(217,70,239,.28)]'
};

export const TimelineTracks = memo(function TimelineTracks() {
  const { duration, currentTime, tracks, setCurrentTime, moveBlock, selectBlock, zoom, setZoom } = useTimelineStore();
  const containerRef = useRef<HTMLDivElement>(null);
  const pxPerSecond = useMemo(() => 56 * zoom, [zoom]);
  const mounted = useMounted();

  const cursorLeft = secondsToPixels(currentTime, pxPerSecond);

  if (!mounted) return <div className="h-[460px] rounded-[2rem] border border-white/10 bg-white/5" />;

  return (
    <section className="rounded-[2.4rem] border border-white/15 bg-[#0e172a]/74 p-7 shadow-[inset_0_1px_0_rgba(255,255,255,.14),0_40px_110px_rgba(0,0,0,.55)] backdrop-blur-3xl">
      <div className="mb-6 flex items-center justify-between">
        <p className="text-sm font-semibold uppercase tracking-[0.28em] text-slate-200">Cinematic Timeline</p>
        <div className="flex items-center gap-4 rounded-xl border border-white/10 bg-[#0a1122]/76 px-4 py-2.5">
          <span className="text-sm text-slate-300">Zoom {zoom.toFixed(1)}x</span>
          <input type="range" min={0.5} max={3} step={0.1} value={zoom} onChange={(e) => setZoom(Number(e.target.value))} className="w-64 accent-cyan-400" />
        </div>
      </div>
      <div
        ref={containerRef}
        className="relative overflow-x-auto rounded-[1.5rem] border border-white/12 bg-[#060b15] p-5 shadow-[inset_0_2px_26px_rgba(0,0,0,.48)]"
        onClick={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          const timelineX = e.clientX - rect.left + e.currentTarget.scrollLeft;
          setCurrentTime(pixelsToSeconds(timelineX, pxPerSecond));
        }}
        onMouseMove={(e) => {
          if (e.buttons !== 1) return;
          const rect = e.currentTarget.getBoundingClientRect();
          setCurrentTime(pixelsToSeconds(e.clientX - rect.left + e.currentTarget.scrollLeft, pxPerSecond));
        }}
      >
        <div style={{ width: secondsToPixels(duration, pxPerSecond) }} className="relative min-w-full">
          <div className="mb-5 h-14 rounded-xl border border-white/10 bg-[linear-gradient(to_right,rgba(255,255,255,.16)_1px,transparent_1px)] [background-size:56px_100%] px-4 text-xs leading-[3.5rem] tracking-[0.2em] text-slate-300">RULER · 24FPS · MASTER</div>
          <div className="pointer-events-none absolute bottom-0 top-0 z-20 w-[3px] rounded-full bg-red-400 shadow-[0_0_22px_rgba(248,113,113,.95),0_0_48px_rgba(248,113,113,.55)]" style={{ left: cursorLeft }} />
          {(Object.keys(tracks) as TrackType[]).map((name) => (
            <div key={name} className="mb-4 grid grid-cols-[170px_1fr] items-center gap-4 last:mb-1">
              <p className="rounded-xl border border-white/12 bg-white/[0.04] px-4 py-4 text-xs uppercase tracking-[0.2em] text-slate-300">{name}</p>
              <div className="relative h-20 rounded-xl border border-white/12 bg-slate-900/90 shadow-[inset_0_2px_18px_rgba(0,0,0,.45)]">
                <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_bottom,rgba(255,255,255,.03)_0%,transparent_20%,transparent_80%,rgba(255,255,255,0.08)_100%)]" />
                <div className="pointer-events-none absolute inset-0 opacity-35 [background-image:linear-gradient(to_right,rgba(255,255,255,0.08)_1px,transparent_1px)] [background-size:14px_100%]" />
                {tracks[name].slice(0, 300).map((block) => (
                  <motion.div
                    key={block.id}
                    drag="x"
                    dragMomentum={false}
                    whileHover={{ scale: 1.02, y: -3 }}
                    onClick={() => {
                      setCurrentTime(block.start);
                      selectBlock(block.id);
                    }}
                    onDragEnd={(_, info) => {
                      const deltaSec = pixelsToSeconds(info.offset.x, pxPerSecond);
                      moveBlock(name, block.id, block.start + deltaSec, block.end + deltaSec);
                    }}
                    className={`absolute top-3 h-14 rounded-xl border bg-gradient-to-r px-4 text-sm font-semibold leading-[3.5rem] text-white ${trackStyles[name]}`}
                    style={{ left: secondsToPixels(block.start, pxPerSecond), width: secondsToPixels(block.end - block.start, pxPerSecond) }}
                  >
                    {block.label} {name === 'hooks' && <span className="ml-2 rounded bg-black/35 px-2 py-0.5 text-[10px]">VIRAL</span>}
                  </motion.div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
});
