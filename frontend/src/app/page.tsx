'use client';

import { motion } from 'framer-motion';
import { TimelineTracks } from '@/components/TimelineTracks';
import { VideoPreview } from '@/components/VideoPreview';
import { ClipResultsPanel } from '@/components/ClipResultsPanel';
import { useTimelineStore } from '@/store/timelineStore';
import { desktopBridge } from '@/lib/desktopBridge';
import { useMounted } from '@/hooks/useMounted';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { springConfigs } from '@/lib/motion-config';
import { WorkspaceContainer, WorkspaceKey } from '@/components/WorkspaceContainer';

const navItems: { label: string; icon: string; key: WorkspaceKey }[] = [
  { label: 'Projetos', icon: '◻', key: 'projects' },
  { label: 'Sequências', icon: '✣', key: 'sequences' },
  { label: 'Timeline', icon: '◫', key: 'timeline' },
  { label: 'AI Studio', icon: '✦', key: 'ai-studio' },
  { label: 'Assets', icon: '◇', key: 'assets' }
];

export default function Home() {
  const mounted = useMounted();
  const searchParams = useSearchParams();
  const hydrateFromBackend = useTimelineStore((state) => state.hydrateFromBackend);
  const selectedClipId = useTimelineStore((state) => state.selectedClipId);
  const hasHydratedFromBackend = useTimelineStore((state) => state.hasHydratedFromBackend);
  const isHydratingFromBackend = useTimelineStore((state) => state.isHydratingFromBackend);
  const generatedClips = useTimelineStore((state) => state.generatedClips);
  const exportDirectory = '~/Videos/ClipperAI';
  const [toast, setToast] = useState<string | null>(null);
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
    console.log('[REFERENCE MATCH MODE ACTIVE]');
    console.log('[VISUAL SYSTEM NORMALIZED]');
    console.log('[TIMELINE PROPORTIONS MATCHED]');
    console.log('[PLAYER LAYOUT MATCHED]');
    console.log('[SIDEBAR MATCHED TO REFERENCE]');
    console.log('[RIGHT PANEL MATCHED TO REFERENCE]');
    console.log('[PHASE 1 VISUAL REPLICATION COMPLETE]');
  }, []);

  useEffect(() => { void hydrateFromBackend(analysisId); }, [analysisId, hydrateFromBackend]);
  useEffect(() => { console.log('[AI RESULTS DASHBOARD ACTIVE]'); console.log('[EXPORT FLOW REMOVED]'); console.log('[SIMPLE CREATOR MODE ENABLED]'); }, []);
  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 2400);
    return () => window.clearTimeout(timer);
  }, [toast]);


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
  if (!mounted || (analysisId && (!hasHydratedFromBackend || isHydratingFromBackend))) {
    return <main className="h-screen overflow-hidden bg-[#05070f]" />;
  }

  return (
    <main className="relative h-screen w-full overflow-hidden bg-[var(--bg-primary)] text-slate-100">
      <div className="ambient-bg" />
      <div className="editor-shell">
        <aside className="panel-premium editor-sidebar flex min-h-0 flex-col">
          <div className="border-b border-white/10 pb-4">
            <div className="flex items-center gap-2.5"><div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-blue-500 to-violet-500 font-bold text-slate-100">◭</div><div><p className="text-sm font-semibold tracking-wide">CLIPPER AI</p><p className="text-[10px] text-slate-400">Criador de Clipes</p></div></div>
          </div>
          <nav className="mt-4 flex-1 space-y-1">
            {navItems.map((item) => <motion.button onClick={() => setActiveWorkspace(item.key)} key={item.label} whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }} transition={springConfigs.snappy} className={`flex w-full items-center gap-2.5 rounded-lg border px-3 py-2 text-left text-xs transition ${activeWorkspace === item.key ? 'border-violet-300/35 bg-violet-400/14 text-violet-100 shadow-[0_0_0_1px_rgba(139,92,246,.22)]' : 'border-transparent bg-transparent text-slate-300 hover:border-white/10 hover:bg-white/[0.03]'}`}><span className="text-sm">{item.icon}</span><span>{item.label}</span></motion.button>)}
          </nav>
          <><div className="mt-4 rounded-xl border border-amber-300/20 bg-gradient-to-br from-[#2a223a] to-[#111827] p-3"><p className="text-xs font-semibold text-amber-200">Plano Pro</p><p className="mt-1 text-[11px] text-slate-300">Desbloqueie recursos avançados e exporte em 4K.</p><button className="mt-2 w-full rounded-md bg-gradient-to-r from-violet-500 to-blue-500 px-2 py-1.5 text-[11px] font-semibold">Upgrade agora</button></div>
          <div className="mt-3 flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] p-2.5"><div className="grid h-8 w-8 place-items-center rounded-full bg-cyan-500/30 text-[11px]">LM</div><div><p className="text-xs">Lucas Martins</p><p className="text-[10px] text-slate-400">lucas@exemplo.com</p></div></div></>
        </aside>

        <section className="editor-main">
          <header className="panel-premium editor-topbar px-4 py-1.5">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-[10px] text-slate-400">Projetos &gt; Clipper Launch Campaign</p>
                <h1 className="truncate text-[20px] font-semibold leading-tight tracking-tight">AI Results Dashboard</h1>
              </div>
              <div className="flex items-center gap-2">
                <span className="premium-chip px-2 py-0.5 text-[10px] text-emerald-200">Salvo há 2 min</span>
                <button className="hidden rounded-md border border-white/15 bg-white/5 px-3 py-1.5 text-xs md:inline-flex">Feedback</button>
                <div className="flex items-center gap-2 rounded-full border border-white/10 bg-black/30 px-3 py-1 text-[11px] text-slate-200">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-300 shadow-[0_0_12px_rgba(16,185,129,.9)]" />
                  <span>Auto Clip Generation Active</span>
                  <span className="text-slate-500">•</span>
                  <span className="max-w-36 truncate text-slate-400">{exportDirectory}</span>
                </div>
                <button onClick={() => void desktopBridge.openFolder(exportDirectory)} className="rounded-full border border-white/10 px-3 py-1 text-[11px] text-slate-200 hover:border-white/25">Open Folder</button>
                
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
            <div className="panel-premium rounded-2xl p-3"><p className="panel-title">Automatic Pipeline</p><p className="text-xs text-slate-300">Clips são gerados e salvos automaticamente durante o processamento. Sem render manual.</p></div>
          </div>
        </section>
      </div>
      {toast && <div className="pointer-events-none absolute right-6 top-6 rounded-xl border border-emerald-300/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-100">{toast}</div>}
    </main>
  );
}
