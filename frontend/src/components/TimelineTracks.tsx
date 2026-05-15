'use client';

import { memo, useMemo, useRef } from 'react';
import { useMounted } from '@/hooks/useMounted';
import { motion } from 'framer-motion';
import { pixelsToSeconds, secondsToPixels } from '@/lib/timelineEngine';
import { TrackType, useTimelineStore } from '@/store/timelineStore';

const trackStyles: Record<TrackType, string> = {
  subtitles: 'from-cyan-500/80 to-cyan-300/70 border-cyan-200/60',
  broll: 'from-violet-500/80 to-purple-300/70 border-violet-200/60',
  hooks: 'from-rose-500/85 to-orange-400/70 border-rose-200/60',
  cuts: 'from-amber-500/80 to-yellow-300/70 border-amber-200/60',
  effects: 'from-fuchsia-500/80 to-purple-300/70 border-fuchsia-200/60'
};

export const TimelineTracks = memo(function TimelineTracks() {
  const { duration, currentTime, tracks, setCurrentTime, moveBlock, selectBlock, zoom, setZoom } = useTimelineStore();
  const containerRef = useRef<HTMLDivElement>(null);
  const pxPerSecond = useMemo(() => 42 * zoom, [zoom]);
  const mounted = useMounted();

  const cursorLeft = secondsToPixels(currentTime, pxPerSecond);

  if (!mounted) return <div className="h-[420px] rounded-[2rem] border border-white/10 bg-white/5" />;

  return (
    <section className="rounded-[2.25rem] border border-white/15 bg-[#101a2e]/70 p-6 shadow-[inset_0_1px_0_rgba(255,255,255,.12),0_35px_100px_rgba(0,0,0,.52)] backdrop-blur-3xl">
      <div className="mb-5 flex items-center justify-between">
        <p className="text-sm font-semibold uppercase tracking-[0.24em] text-slate-300">Timeline</p>
        <div className="flex items-center gap-4 rounded-xl border border-white/10 bg-[#0a1122]/70 px-3 py-2">
          <span className="text-sm text-slate-300">Zoom {zoom.toFixed(1)}x</span>
          <input type="range" min={0.5} max={3} step={0.1} value={zoom} onChange={(e) => setZoom(Number(e.target.value))} className="w-64 accent-cyan-400" />
        </div>
      </div>
      <div
        ref={containerRef}
        className="relative overflow-x-auto rounded-2xl border border-white/12 bg-[#070d1a] p-4 shadow-[inset_0_2px_24px_rgba(0,0,0,.35)]"
        onMouseMove={(e) => {
          if (e.buttons !== 1) return;
          const rect = e.currentTarget.getBoundingClientRect();
          setCurrentTime(pixelsToSeconds(e.clientX - rect.left + e.currentTarget.scrollLeft, pxPerSecond));
        }}
      >
        <div style={{ width: secondsToPixels(duration, pxPerSecond) }} className="relative min-w-full">
          <div className="mb-4 h-10 rounded-xl border border-white/10 bg-[linear-gradient(to_right,rgba(255,255,255,.12)_1px,transparent_1px)] [background-size:42px_100%] px-3 text-[11px] leading-10 tracking-[0.13em] text-slate-400">RULER</div>
          <div className="pointer-events-none absolute bottom-0 top-0 z-20 w-[3px] rounded-full bg-red-400 shadow-[0_0_22px_rgba(248,113,113,.95)]" style={{ left: cursorLeft }} />
          {(Object.keys(tracks) as TrackType[]).map((name) => (
            <div key={name} className="mb-4 grid grid-cols-[150px_1fr] items-center gap-4 last:mb-1">
              <p className="rounded-xl border border-white/12 bg-white/[0.04] px-3 py-3 text-xs uppercase tracking-[0.18em] text-slate-300">{name}</p>
              <div className="relative h-16 rounded-xl border border-white/12 bg-slate-900/85 shadow-[inset_0_2px_18px_rgba(0,0,0,.45)]">
                <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_bottom,transparent_0%,transparent_80%,rgba(255,255,255,0.06)_100%)]" />
                {tracks[name].map((block) => (
                  <motion.div
                    key={block.id}
                    drag="x"
                    dragMomentum={false}
                    whileHover={{ scale: 1.02, y: -2 }}
                    onClick={() => {
                      selectBlock(block.id);
                      setCurrentTime(block.start);
                    }}
                    onDragEnd={(_, info) => {
                      const deltaSec = pixelsToSeconds(info.offset.x, pxPerSecond);
                      moveBlock(name, block.id, block.start + deltaSec, block.end + deltaSec);
                    }}
                    className={`absolute top-2.5 h-11 rounded-xl border bg-gradient-to-r px-3 text-sm font-medium leading-[2.75rem] text-white shadow-[0_10px_20px_rgba(0,0,0,.4)] ${trackStyles[name]}`}
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
