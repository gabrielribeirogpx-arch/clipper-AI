'use client';

import { InspectorPanel } from '@/components/InspectorPanel';
import { TimelineTracks } from '@/components/TimelineTracks';
import { VideoPreview } from '@/components/VideoPreview';
import { useTimelineStore } from '@/store/timelineStore';
import { useMounted } from '@/hooks/useMounted';

function RenderQueuePanel() {
  const { renderQueue } = useTimelineStore();
  const color = { queued: 'bg-slate-500', rendering: 'bg-cyan-500', completed: 'bg-emerald-500', failed: 'bg-rose-500' } as const;

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <h3 className="mb-3 text-sm font-semibold">Render Queue</h3>
      <div className="space-y-3">
        {renderQueue.map((job) => (
          <div key={job.id} className="rounded-lg border border-white/10 p-2">
            <div className="mb-1 flex items-center justify-between text-xs">
              <span>{job.clipName}</span>
              <span className="capitalize text-slate-300">{job.state}</span>
            </div>
            <div className="h-1.5 rounded bg-slate-800">
              <div className={`h-1.5 rounded ${color[job.state]}`} style={{ width: `${job.progress}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Home() {
  const mounted = useMounted();

  if (!mounted) {
    return (
      <main className="min-h-screen bg-[radial-gradient(circle_at_15%_20%,rgba(56,189,248,.18),transparent_42%),radial-gradient(circle_at_80%_0%,rgba(168,85,247,.2),transparent_35%),linear-gradient(140deg,#020617,#0f172a_45%,#000)] p-6 text-slate-100">
        <h1 className="mb-6 text-2xl font-bold tracking-tight">Clipper AI • Cinematic Timeline Editor</h1>
        <div className="grid gap-6 lg:grid-cols-[360px_1fr_340px]">
          <div className="h-80 animate-pulse rounded-2xl bg-white/5" />
          <div className="h-80 animate-pulse rounded-2xl bg-white/5" />
          <div className="h-80 animate-pulse rounded-2xl bg-white/5" />
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_15%_20%,rgba(56,189,248,.18),transparent_42%),radial-gradient(circle_at_80%_0%,rgba(168,85,247,.2),transparent_35%),linear-gradient(140deg,#020617,#0f172a_45%,#000)] p-6 text-slate-100">
      <h1 className="mb-6 text-2xl font-bold tracking-tight">Clipper AI • Cinematic Timeline Editor</h1>
      <div className="grid gap-6 lg:grid-cols-[360px_1fr_340px]">
        <div className="space-y-6">
          <VideoPreview />
          <RenderQueuePanel />
        </div>
        <TimelineTracks />
        <InspectorPanel />
      </div>
    </main>
  );
}
