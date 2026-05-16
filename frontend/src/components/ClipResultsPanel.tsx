'use client';

import { useMemo } from 'react';
import { GeneratedClip, useTimelineStore } from '@/store/timelineStore';

const rankBadge = (score: number) => {
  if (score >= 85) return '🔥 Top Viral';
  if (score >= 70) return 'High Potential';
  return 'Medium Potential';
};

function ClipCard({ clip }: { clip: GeneratedClip }) {
  const { selectClip, selectedClipId } = useTimelineStore();
  const selected = selectedClipId === clip.id;

  return (
    <button
      onClick={() => selectClip(clip.id)}
      className={`w-full rounded-2xl border p-4 text-left transition ${selected ? 'border-cyan-300/60 bg-cyan-500/10' : 'border-white/10 bg-[#0a1122]/80 hover:border-white/30'}`}
    >
      <video src={`http://localhost:8000${clip.preview_video}`} muted className="mb-3 aspect-video w-full rounded-xl border border-white/10 object-cover" />
      <div className="mb-2 flex items-center justify-between">
        <p className="text-sm font-semibold text-white">{clip.label}</p>
        <span className="text-xs text-cyan-200">{rankBadge(clip.viral_score)}</span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs text-slate-300">
        <span>Viral: {clip.viral_score}</span><span>Hook: {clip.hook_score}</span>
        <span>Retention: {clip.retention_score}</span><span>Emotion: {clip.emotion_score}</span>
        <span>Duration: {clip.duration}s</span><span>{clip.start.toFixed(1)}s → {clip.end.toFixed(1)}s</span>
      </div>
    </button>
  );
}

export function ClipResultsPanel() {
  const { generatedClips } = useTimelineStore();
  const clips = useMemo(() => generatedClips, [generatedClips]);

  return (
    <div className="rounded-[2.1rem] border border-white/15 bg-[#101a2e]/72 p-6 shadow-[inset_0_1px_0_rgba(255,255,255,.12),0_35px_90px_rgba(0,0,0,.5)]">
      <h3 className="mb-5 text-sm font-semibold uppercase tracking-[0.24em] text-slate-200">AI Viral Clips</h3>
      <div className="grid max-h-[560px] gap-4 overflow-auto pr-1">
        {clips.map((clip) => <ClipCard key={clip.id} clip={clip} />)}
        {!clips.length && <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">No generated clips yet.</div>}
      </div>
    </div>
  );
}
