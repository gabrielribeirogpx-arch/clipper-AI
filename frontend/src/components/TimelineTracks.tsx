'use client';

import { memo, useMemo, useRef } from 'react';
import { useMounted } from '@/hooks/useMounted';
import { motion } from 'framer-motion';
import { pixelsToSeconds, secondsToPixels } from '@/lib/timelineEngine';
import { TrackType, useTimelineStore } from '@/store/timelineStore';

const trackStyles: Record<TrackType, string> = {
  subtitles: 'from-cyan-500/70 to-cyan-300/60 border-cyan-200/60',
  broll: 'from-violet-500/70 to-purple-300/60 border-violet-200/60',
  hooks: 'from-rose-500/75 to-orange-400/65 border-rose-200/60',
  cuts: 'from-amber-500/70 to-yellow-300/60 border-amber-200/60',
  effects: 'from-fuchsia-500/70 to-purple-300/60 border-fuchsia-200/60'
};

export const TimelineTracks = memo(function TimelineTracks() {
  const { duration, currentTime, tracks, setCurrentTime, moveBlock, selectBlock, zoom, setZoom } = useTimelineStore();
  const containerRef = useRef<HTMLDivElement>(null);
  const pxPerSecond = useMemo(() => 36 * zoom, [zoom]);
  const mounted = useMounted();

  const cursorLeft = secondsToPixels(currentTime, pxPerSecond);

  if (!mounted) return <div className="h-72 rounded-2xl border border-white/10 bg-white/5" />;

  return (
    <section className="rounded-3xl border border-white/10 bg-[#111827]/70 p-4 shadow-2xl backdrop-blur-2xl">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Timeline</p>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-300">Zoom {zoom.toFixed(1)}x</span>
          <input type="range" min={0.5} max={3} step={0.1} value={zoom} onChange={(e) => setZoom(Number(e.target.value))} className="w-52 accent-cyan-400" />
        </div>
      </div>
      <div
        ref={containerRef}
        className="relative overflow-x-auto rounded-2xl border border-white/10 bg-[#0b1222] p-3"
        onMouseMove={(e) => {
          if (e.buttons !== 1) return;
          const rect = e.currentTarget.getBoundingClientRect();
          setCurrentTime(pixelsToSeconds(e.clientX - rect.left + e.currentTarget.scrollLeft, pxPerSecond));
        }}
      >
        <div style={{ width: secondsToPixels(duration, pxPerSecond) }} className="relative min-w-full">
          <div className="mb-3 h-6 rounded bg-[linear-gradient(to_right,rgba(255,255,255,.08)_1px,transparent_1px)] [background-size:36px_100%] px-2 text-[10px] text-slate-400" />
          <div className="pointer-events-none absolute bottom-0 top-0 z-20 w-0.5 bg-red-500 shadow-[0_0_15px_rgba(239,68,68,.8)]" style={{ left: cursorLeft }} />
          {(Object.keys(tracks) as TrackType[]).map((name) => (
            <div key={name} className="mb-3 grid grid-cols-[120px_1fr] items-center gap-3">
              <p className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs uppercase tracking-[0.15em] text-slate-300">{name}</p>
              <div className="relative h-12 rounded-xl border border-white/10 bg-slate-900/80">
                {tracks[name].map((block) => (
                  <motion.div
                    key={block.id}
                    drag="x"
                    dragMomentum={false}
                    whileHover={{ scale: 1.02, y: -1 }}
                    onClick={() => {
                      selectBlock(block.id);
                      setCurrentTime(block.start);
                    }}
                    onDragEnd={(_, info) => {
                      const deltaSec = pixelsToSeconds(info.offset.x, pxPerSecond);
                      moveBlock(name, block.id, block.start + deltaSec, block.end + deltaSec);
                    }}
                    className={`absolute top-1.5 h-9 rounded-xl border bg-gradient-to-r px-2 text-xs leading-9 text-white shadow-lg ${trackStyles[name]}`}
                    style={{ left: secondsToPixels(block.start, pxPerSecond), width: secondsToPixels(block.end - block.start, pxPerSecond) }}
                  >
                    {block.label} {name === 'hooks' && <span className="ml-2 rounded bg-black/30 px-1.5 py-0.5 text-[10px]">VIRAL</span>}
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
