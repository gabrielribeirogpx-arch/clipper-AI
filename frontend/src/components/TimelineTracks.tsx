'use client';

import { motion } from 'framer-motion';
import { useTimelineStore } from '@/store/timelineStore';

const trackStyles: Record<string, string> = {
  subtitles: 'bg-cyan-500/30 border-cyan-300/40',
  broll: 'bg-violet-500/30 border-violet-300/40',
  hooks: 'bg-emerald-500/30 border-emerald-300/40',
  cuts: 'bg-amber-500/30 border-amber-300/40'
};

export function TimelineTracks() {
  const { duration, currentTime, subtitles, broll, hooks, cuts, setCurrentTime } = useTimelineStore();
  const tracks = { subtitles, broll, hooks, cuts };

  return (
    <div className="rounded-2xl border border-slate-700 bg-card p-4">
      <input type="range" min={0} max={duration} step={0.1} value={currentTime} onChange={(e) => setCurrentTime(Number(e.target.value))} className="mb-4 w-full" />
      {Object.entries(tracks).map(([name, blocks]) => (
        <div key={name} className="mb-3">
          <p className="mb-2 text-xs uppercase tracking-wider text-slate-400">{name}</p>
          <div className="relative h-12 rounded bg-slate-900">
            {blocks.map((block) => (
              <motion.div
                key={block.id}
                drag="x"
                className={`absolute top-1 h-10 rounded border px-2 text-xs leading-10 ${trackStyles[name]}`}
                style={{
                  left: `${(block.start / duration) * 100}%`,
                  width: `${((block.end - block.start) / duration) * 100}%`
                }}
              >
                {block.label}
              </motion.div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
