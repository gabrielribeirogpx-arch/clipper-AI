'use client';

import { motion } from 'framer-motion';
import { InspectorPanel } from '@/components/InspectorPanel';
import { TimelineTracks } from '@/components/TimelineTracks';
import { VideoPreview } from '@/components/VideoPreview';
import { ClipResultsPanel } from '@/components/ClipResultsPanel';
import { useTimelineStore } from '@/store/timelineStore';
import { exportClip } from '@/lib/api';
import { useMounted } from '@/hooks/useMounted';
import { useEffect } from 'react';
import { useSearchParams } from 'next/navigation';

const navItems = [
  { label: 'Projects', icon: '◻', active: false },
  { label: 'Sequences', icon: '◉', active: false },
  { label: 'Timeline', icon: '▦', active: true },
  { label: 'AI Studio', icon: '✦', active: false },
  { label: 'Assets', icon: '◈', active: false }
];

function RenderQueuePanel() {
  const { renderQueue } = useTimelineStore();
  const color = { queued: 'from-slate-500 to-slate-300', rendering: 'from-cyan-400 to-blue-400', completed: 'from-emerald-400 to-teal-300', failed: 'from-rose-400 to-orange-300' } as const;

  return <div className="panel-premium p-5">
    <h3 className="panel-title">Render Queue</h3>
    <div className="space-y-3">
      {renderQueue.map((job) => <div key={job.id} className="rounded-2xl bg-white/[0.03] p-3">
        <div className="mb-2 flex items-center justify-between text-sm"><span>{job.clipName}</span><span className="text-slate-400">{job.state}</span></div>
        <div className="h-1.5 rounded-full bg-white/10"><div className={`h-1.5 rounded-full bg-gradient-to-r ${color[job.state]}`} style={{ width: `${job.progress}%` }} /></div>
      </div>)}
    </div>
  </div>;
}

export default function Home() {
  const mounted = useMounted();
  const searchParams = useSearchParams();
  const hydrateFromBackend = useTimelineStore((state) => state.hydrateFromBackend);
  const selectedClipId = useTimelineStore((state) => state.selectedClipId);
  const analysisId = searchParams.get('analysis_id');

  useEffect(() => { void hydrateFromBackend(analysisId); }, [analysisId, hydrateFromBackend]);
  if (!mounted) return <main className="min-h-screen bg-[#050505]" />;

  const handleExport = async () => {
    if (!selectedClipId) return;
    try {
      const data = await exportClip(selectedClipId);
      if (data.success && data.download_url) {
        const downloadUrl = `http://localhost:8000${data.download_url}`;
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = downloadUrl.split('/').pop() ?? 'clip.mp4';
        document.body.appendChild(link); link.click(); link.remove();
      }
      await hydrateFromBackend();
    } catch (err) { console.error('[EXPORT ERROR]', err); }
  };

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#050505] text-slate-100">
      <div className="ambient-bg" />
      <div className="relative mx-auto grid min-h-screen max-w-[2200px] grid-cols-1 gap-6 px-6 py-6 xl:grid-cols-[240px_1fr_420px]">
        <aside className="panel-premium h-fit p-4">
          <div className="mb-8 flex items-center gap-3"><div className="grid h-11 w-11 place-items-center rounded-2xl bg-white/10">✂</div><div><p className="text-xs tracking-[0.25em] text-slate-300">CLIPPER AI</p><p className="text-xs text-slate-500">Creative OS</p></div></div>
          <nav className="space-y-1.5">{navItems.map((item) => <motion.button key={item.label} whileHover={{ x: 4 }} transition={{ type: 'spring', stiffness: 260, damping: 20 }} className={`flex w-full items-center gap-3 rounded-full px-3 py-2.5 text-sm ${item.active ? 'bg-white/12 text-white' : 'text-slate-400 hover:bg-white/6 hover:text-slate-200'}`}><span>{item.icon}</span><span>{item.label}</span></motion.button>)}</nav>
        </aside>

        <section className="space-y-5">
          <header className="panel-premium flex items-center justify-between px-5 py-4">
            <div><p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">Current Sequence</p><h1 className="text-3xl font-semibold tracking-tight">Clipper Launch Campaign</h1></div>
            <div className="flex items-center gap-2"><span className="rounded-full bg-white/10 px-3 py-1 text-xs">AI Online</span><button onClick={handleExport} className="rounded-full bg-white/10 px-4 py-2 text-sm">Render</button><button onClick={handleExport} className="rounded-full bg-gradient-to-r from-cyan-300 to-blue-400 px-4 py-2 text-sm font-semibold text-slate-950">Export</button></div>
          </header>
          <VideoPreview />
          <TimelineTracks />
        </section>

        <section className="space-y-5">
          <ClipResultsPanel />
          <InspectorPanel />
          <RenderQueuePanel />
        </section>
      </div>
    </main>
  );
}
