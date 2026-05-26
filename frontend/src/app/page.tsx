'use client';

import { motion } from 'framer-motion';
import { InspectorPanel } from '@/components/InspectorPanel';
import { TimelineTracks } from '@/components/TimelineTracks';
import { VideoPreview } from '@/components/VideoPreview';
import { ClipResultsPanel } from '@/components/ClipResultsPanel';
import { useTimelineStore } from '@/store/timelineStore';
import { exportClip } from '@/lib/api';
import { useMounted } from '@/hooks/useMounted';
import { useEffect, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import { springConfigs } from '@/lib/motion-config';

const navItems = [
  { label: 'Projects', icon: '⌘' },
  { label: 'Sequences', icon: '◍' },
  { label: 'Timeline', icon: '▤', active: true },
  { label: 'AI Studio', icon: '✦' },
  { label: 'Assets', icon: '◈' }
];

export default function Home() {
  const mounted = useMounted();
  const searchParams = useSearchParams();
  const hydrateFromBackend = useTimelineStore((state) => state.hydrateFromBackend);
  const selectedClipId = useTimelineStore((state) => state.selectedClipId);
  const analysisId = searchParams.get('analysis_id');
  const heroRef = useRef<HTMLElement | null>(null);
  
  useEffect(() => {
    console.log('[FINAL VISUAL REFINEMENT ACTIVE]');
    console.log('[VIDEO AREA EXPANDED]');
    console.log('[TIMELINE DENSITY REDUCED]');
    console.log('[PLAYER CARD COMPACTED]');
  }, []);

  useEffect(() => { void hydrateFromBackend(analysisId); }, [analysisId, hydrateFromBackend]);

  if (!mounted) return <main className="h-screen overflow-hidden bg-[#05070f]" />;

  const handleExport = async () => {
    if (!selectedClipId) return;
    const data = await exportClip(selectedClipId);
    if (data.success && data.download_url) {
      const downloadUrl = `http://localhost:8000${data.download_url}`;
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = downloadUrl.split('/').pop() ?? 'clip.mp4';
      document.body.appendChild(link); link.click(); link.remove();
    }
    await hydrateFromBackend();
  };

  return (
    <main className="relative h-screen w-full overflow-hidden bg-[var(--bg-primary)] text-slate-100">
      <div className="ambient-bg" />
      <div className="editor-shell">
        <aside className="panel-premium editor-sidebar flex min-h-0 flex-col">
          <div className="border-b border-white/10 pb-5">
            <div className="flex items-center gap-3"><div className="grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-cyan-400 to-indigo-500 font-bold text-slate-950">✂</div><div><p className="text-lg font-semibold">Clipper AI</p><p className="text-xs tracking-[0.18em] text-slate-400">Creative OS</p></div></div>
          </div>
          <nav className="mt-6 flex-1 space-y-2">
            {navItems.map((item) => <motion.button key={item.label} whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} transition={springConfigs.snappy} className={`flex w-full items-center gap-3 rounded-xl border px-3 py-2.5 text-left text-sm transition ${item.active ? 'border-cyan-300/35 bg-cyan-400/10 text-cyan-100 shadow-[0_0_0_1px_rgba(56,189,248,.22)]' : 'border-white/5 bg-white/[0.02] text-slate-300 hover:border-white/15 hover:bg-white/[0.04]'}`}><span>{item.icon}</span><span>{item.label}</span></motion.button>)}
          </nav>
          <><div className="mt-5 rounded-2xl border border-violet-300/25 bg-gradient-to-br from-violet-500/14 to-cyan-400/8 p-3"><p className="text-xs uppercase tracking-[0.17em] text-violet-200">Pro Plan</p><p className="mt-2 text-sm text-slate-300">8K exports · team review · AI scenes</p></div>
          <div className="mt-3 flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.03] p-3"><div className="grid h-9 w-9 place-items-center rounded-xl bg-slate-600/60">AM</div><div><p className="text-sm">Ana Martins</p><p className="text-xs text-slate-400">Founder</p></div></div></>
        </aside>

        <section className="editor-main">
          <header className="panel-premium editor-topbar px-4 py-3">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Workspace / Campaigns / Q2</p>
                <h1 className="mt-1 text-xl font-semibold tracking-tight lg:text-2xl">Clipper Launch Campaign</h1>
              </div>
              <div className="flex items-center gap-2">
                <span className="premium-chip px-3 py-1 text-xs text-cyan-200">AI Online</span>
                <button className="hidden rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm md:inline-flex">Feedback</button>
                <button onClick={handleExport} className="rounded-xl bg-gradient-to-r from-cyan-300 to-indigo-300 px-4 py-2 text-sm font-semibold text-slate-950 lg:px-5 lg:py-2.5">Exportar</button>
              </div>
            </div>
          </header>
          <VideoPreview sectionRef={heroRef} />
          <TimelineTracks />
        </section>

        <section className="editor-right min-h-0 min-w-0 space-y-2">
          <ClipResultsPanel />
          <InspectorPanel />
        </section>
      </div>
    </main>
  );
}
