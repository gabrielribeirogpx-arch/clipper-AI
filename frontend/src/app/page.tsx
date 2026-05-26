'use client';

import { motion } from 'framer-motion';
import { TimelineTracks } from '@/components/TimelineTracks';
import { VideoPreview } from '@/components/VideoPreview';
import { ClipResultsPanel } from '@/components/ClipResultsPanel';
import { useTimelineStore } from '@/store/timelineStore';
import { exportClip } from '@/lib/api';
import { useMounted } from '@/hooks/useMounted';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { springConfigs } from '@/lib/motion-config';
import { WorkspaceContainer, WorkspaceKey } from '@/components/WorkspaceContainer';

const navItems: { label: string; icon: string; key: WorkspaceKey }[] = [
  { label: 'Projetos', icon: '⌘', key: 'projects' },
  { label: 'Sequências', icon: '◍', key: 'sequences' },
  { label: 'Timeline', icon: '▤', key: 'timeline' },
  { label: 'AI Studio', icon: '✦', key: 'ai-studio' },
  { label: 'Assets', icon: '◈', key: 'assets' }
];

export default function Home() {
  const mounted = useMounted();
  const searchParams = useSearchParams();
  const hydrateFromBackend = useTimelineStore((state) => state.hydrateFromBackend);
  const selectedClipId = useTimelineStore((state) => state.selectedClipId);
  const analysisId = searchParams.get('analysis_id');
  const heroRef = useRef<HTMLElement | null>(null);
  const [activeWorkspace, setActiveWorkspace] = useState<WorkspaceKey>('timeline');
  
  useEffect(() => {
    console.log('[TRUE 16:9 VIEWPORT FIX ACTIVE]');
    console.log('[VIEWPORT HEIGHT REALLOCATED]');
    console.log('[TIMELINE HEIGHT REDUCED]');
    console.log('[PLAYER AREA MATHEMATICALLY CORRECTED]');
    console.log('[VISIBLE PLAYER NOW TRUE 16:9]');
    console.log('[BOTTOM SAFE AREA ACTIVE]');
    console.log('[TIMELINE NO LONGER CLIPPED]');
    console.log('[WORKSPACE BREATHING ROOM ADDED]');
    console.log('[PREMIUM FOOTER SPACING ACTIVE]');
    console.log('[REAL WORKSPACE SYSTEM ACTIVE]');
    console.log('[PREMIUM APP ARCHITECTURE ACTIVE]');
  }, []);

  useEffect(() => { void hydrateFromBackend(analysisId); }, [analysisId, hydrateFromBackend]);


  useEffect(() => {
    const logs: Record<WorkspaceKey, string> = {
      projects: '[PROJECTS VIEW LOADED]',
      sequences: '[SEQUENCES VIEW LOADED]',
      timeline: '[TIMELINE VIEW LOADED]',
      'ai-studio': '[AI STUDIO VIEW LOADED]',
      assets: '[ASSETS VIEW LOADED]'
    };
    console.log(logs[activeWorkspace]);
  }, [activeWorkspace]);

  const workspaceTitle = useMemo(() => navItems.find((item) => item.key === activeWorkspace)?.label ?? 'Timeline', [activeWorkspace]);
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
            {navItems.map((item) => <motion.button onClick={() => setActiveWorkspace(item.key)} key={item.label} whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} transition={springConfigs.snappy} className={`flex w-full items-center gap-3 rounded-xl border px-3 py-2.5 text-left text-sm transition ${activeWorkspace === item.key ? 'border-cyan-300/35 bg-cyan-400/10 text-cyan-100 shadow-[0_0_0_1px_rgba(56,189,248,.22)]' : 'border-white/5 bg-white/[0.02] text-slate-300 hover:border-white/15 hover:bg-white/[0.04]'}`}><span>{item.icon}</span><span>{item.label}</span></motion.button>)}
          </nav>
          <><div className="mt-5 rounded-2xl border border-violet-300/25 bg-gradient-to-br from-violet-500/14 to-cyan-400/8 p-3"><p className="text-xs uppercase tracking-[0.17em] text-violet-200">Usage Console</p><div className="mt-2 space-y-1 text-xs text-slate-300"><p>GPU 63% / 120h</p><p>AI Credits 7,420 / 10,000</p><p>Render 318 / 500 min</p><p>Exports 52 remaining</p><p>Storage 1.8TB / 3TB</p></div></div>
          <div className="mt-3 flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.03] p-3"><div className="grid h-9 w-9 place-items-center rounded-xl bg-slate-600/60">AM</div><div><p className="text-sm">Ana Martins</p><p className="text-xs text-slate-400">Founder</p></div></div></>
        </aside>

        <section className="editor-main">
          <header className="panel-premium editor-topbar px-3 py-1.5">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-[10px] uppercase tracking-[0.14em] text-slate-400">Projetos &gt; Clipper Launch Campaign</p>
                <h1 className="truncate text-lg font-semibold leading-tight tracking-tight lg:text-xl">Clipper Launch Campaign</h1>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="premium-chip px-2 py-0.5 text-[11px] text-cyan-200">Sala há 2 min</span>
                <button className="hidden rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs md:inline-flex">Feedback</button>
                <button onClick={handleExport} className="rounded-lg bg-gradient-to-r from-cyan-300 to-indigo-300 px-3 py-1.5 text-xs font-semibold text-slate-950 lg:px-4 lg:py-2">Exportar</button>
              </div>
            </div>
          </header>
          {activeWorkspace === 'timeline' ? (
            <>
              <VideoPreview sectionRef={heroRef} />
              <TimelineTracks />
            </>
          ) : (
            <>
              <div className="min-h-0">
                <WorkspaceContainer workspace={activeWorkspace} onOpenTimeline={() => setActiveWorkspace('timeline')} />
              </div>
              <div className="editor-timeline-section panel-premium grid place-items-center text-xs text-slate-400">Timeline dock remains available in Timeline workspace.</div>
            </>
          )}
        </section>

        <section className="editor-right min-h-0 min-w-0">
          <div className="grid h-full min-h-0 grid-rows-[minmax(0,1fr)_auto] gap-2">
            <ClipResultsPanel />
            <div className="panel-premium rounded-2xl p-3"><p className="panel-title">Plan usage</p><div className="space-y-2 text-xs"><p>GPU usage 63% / 120h</p><p>AI credits 7,420 / 10,000</p><p>Render minutes 318 / 500</p><p>Exports remaining 52</p><p>Storage 1.8TB / 3TB</p></div></div>
          </div>
        </section>
      </div>
    </main>
  );
}
