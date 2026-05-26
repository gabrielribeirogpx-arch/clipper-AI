'use client';

import { useMemo, useRef } from 'react';
import { motion } from 'framer-motion';
import { GeneratedClip, useTimelineStore } from '@/store/timelineStore';

const rankBadge = (score: number) => {
  if (score >= 85) return '🔥 Top Viral';
  if (score >= 70) return 'High Potential';
  return 'Medium Potential';
};

function ClipCard({ clip }: { clip: GeneratedClip }) {
  const { selectClip, selectedClipId } = useTimelineStore();
  const selected = selectedClipId === clip.id;

  const videoRef = useRef<HTMLVideoElement | null>(null);
  return (
    <motion.button whileHover={{ y: -4, scale: 1.01 }} transition={{ type: 'spring', stiffness: 280, damping: 22 }}
      onHoverStart={() => videoRef.current?.play()}
      onHoverEnd={() => { if (videoRef.current) { videoRef.current.pause(); videoRef.current.currentTime = 0; } }}
      onClick={() => selectClip(clip.id)}
      className={`w-full rounded-2xl border p-4 text-left transition ${selected ? 'border-cyan-300/60 bg-cyan-500/10' : 'border-white/10 bg-[#0a1122]/80 hover:border-white/30'}`}
    >
      <div className="relative mb-3 overflow-hidden rounded-2xl">
        <video ref={videoRef} src={`http://localhost:8000${clip.final_video}`} muted loop playsInline className="aspect-video w-full object-cover transition duration-500" />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-white/5" />
      </div>
      <div className="mb-2 flex items-center justify-between">
        <p className="text-sm font-semibold text-white">{clip.label}</p>
        <span className="text-xs text-cyan-200">{rankBadge(clip.viral_score)}</span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs text-slate-300">
        <span>Viral: {clip.viral_score}</span><span>Hook: {clip.hook_score}</span>
        <span>Retention: {clip.retention_score}</span><span>Emotion: {clip.emotion_score}</span>
        <span>Duration: {clip.duration}s</span><span>{clip.start.toFixed(1)}s → {clip.end.toFixed(1)}s</span>
      </div>

      <div className="mt-4 rounded-xl border border-white/10 bg-black/20 p-3 text-xs text-slate-200">
        <p className="mb-1 text-[10px] uppercase tracking-[0.18em] text-cyan-200/90">Title</p>
        <p className="text-sm font-semibold text-white">{clip.title}</p>
        <p className="mt-3 mb-1 text-[10px] uppercase tracking-[0.18em] text-cyan-200/90">Description</p>
        <p className="text-slate-300">{clip.description}</p>
        <p className="mt-3 mb-1 text-[10px] uppercase tracking-[0.18em] text-cyan-200/90">Caption</p>
        <p className="text-slate-100">{clip.caption}</p>
        {!!clip.hashtags?.length && (
          <p className="mt-3 text-cyan-200">{clip.hashtags.join(' ')}</p>
        )}
      </div>
    </motion.button>
  );
}

export function ClipResultsPanel() {
  const { generatedClips } = useTimelineStore();
  const clips = useMemo(() => generatedClips, [generatedClips]);

  return (
    <div className="panel-premium p-5">
      <h3 className="mb-5 text-sm font-semibold uppercase tracking-[0.24em] text-slate-200">AI Viral Clips</h3>
      <div className="grid max-h-[560px] gap-4 overflow-auto pr-1">
        {clips.map((clip) => <ClipCard key={clip.id} clip={clip} />)}
        {!clips.length && <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">No generated clips yet.</div>}
      </div>
    </div>
  );
}
