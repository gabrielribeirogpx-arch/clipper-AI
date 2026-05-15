'use client';

import { memo, useMemo, useRef } from 'react';
import { useMounted } from '@/hooks/useMounted';
import { motion } from 'framer-motion';
import { pixelsToSeconds, secondsToPixels } from '@/lib/timelineEngine';
import { TrackType, useTimelineStore } from '@/store/timelineStore';

const trackStyles: Record<TrackType, string> = {
  subtitles: 'bg-cyan-500/30 border-cyan-300/40',
  broll: 'bg-violet-500/30 border-violet-300/40',
  hooks: 'bg-emerald-500/30 border-emerald-300/40',
  cuts: 'bg-amber-500/30 border-amber-300/40',
  effects: 'bg-fuchsia-500/30 border-fuchsia-300/40'
};

export const TimelineTracks = memo(function TimelineTracks() {
  const { duration, currentTime, tracks, setCurrentTime, moveBlock, selectBlock, zoom, setZoom } = useTimelineStore();
  const containerRef = useRef<HTMLDivElement>(null);
  const pxPerSecond = useMemo(() => 36 * zoom, [zoom]);
  const mounted = useMounted();

  const cursorLeft = secondsToPixels(currentTime, pxPerSecond);

  if (!mounted) {
    return (
      <div className="rounded-2xl border border-white/10 bg-white/5 p-4 shadow-2xl backdrop-blur-xl">
        <div className="h-56 animate-pulse rounded-xl bg-slate-900/80" />
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4 shadow-2xl backdrop-blur-xl">
      <div className="mb-3 flex items-center gap-4">
        <input type="range" min={0.5} max={3} step={0.1} value={zoom} onChange={(e) => setZoom(Number(e.target.value))} className="w-40" />
        <span className="text-xs text-slate-300">Zoom: {zoom.toFixed(1)}x</span>
      </div>
      <div
        ref={containerRef}
        className="relative overflow-x-auto rounded-xl bg-slate-950/80 p-3"
        onMouseMove={(e) => {
          if (e.buttons !== 1) return;
          const rect = e.currentTarget.getBoundingClientRect();
          setCurrentTime(pixelsToSeconds(e.clientX - rect.left + e.currentTarget.scrollLeft, pxPerSecond));
        }}
      >
        <div style={{ width: secondsToPixels(duration, pxPerSecond) }} className="relative min-w-full">
          <div className="pointer-events-none absolute bottom-0 top-0 z-10 w-0.5 bg-cyan-300" style={{ left: cursorLeft }} />
          {(Object.keys(tracks) as TrackType[]).map((name) => (
            <div key={name} className="mb-3">
              <p className="mb-2 text-xs uppercase tracking-wider text-slate-400">{name}</p>
              <div className="relative h-12 rounded bg-slate-900/90">
                {tracks[name].map((block) => (
                  <motion.div
                    initial={false}
                    key={block.id}
                    drag="x"
                    dragMomentum={false}
                    onClick={() => {
                      selectBlock(block.id);
                      setCurrentTime(block.start);
                    }}
                    onDragEnd={(_, info) => {
                      const deltaSec = pixelsToSeconds(info.offset.x, pxPerSecond);
                      moveBlock(name, block.id, block.start + deltaSec, block.end + deltaSec);
                    }}
                    className={`absolute top-1 h-10 rounded border px-2 text-xs leading-10 ${trackStyles[name]}`}
                    style={{ left: secondsToPixels(block.start, pxPerSecond), width: secondsToPixels(block.end - block.start, pxPerSecond) }}
                  >
                    {block.label}
                  </motion.div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
});
