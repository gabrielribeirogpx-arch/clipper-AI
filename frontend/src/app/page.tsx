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
  { label: 'Projects', icon: '◻' },
  { label: 'Sequences', icon: '◉' },
  { label: 'Timeline', icon: '▦', active: true },
  { label: 'AI Studio', icon: '✦' },
  { label: 'Assets', icon: '◈' }
];

export default function Home() {
  const mounted = useMounted();
  const searchParams = useSearchParams();
  const hydrateFromBackend = useTimelineStore((state) => state.hydrateFromBackend);
  const selectedClipId = useTimelineStore((state) => state.selectedClipId);
  const analysisId = searchParams.get('analysis_id');
  const layoutRef = useRef<HTMLDivElement | null>(null);
  const sidebarRef = useRef<HTMLElement | null>(null);
  const mainContentRef = useRef<HTMLElement | null>(null);
  const heroRef = useRef<HTMLElement | null>(null);

  useEffect(() => { void hydrateFromBackend(analysisId); }, [analysisId, hydrateFromBackend]);

  useEffect(() => {
    if (!mounted) return;

    const logLayoutMetrics = () => {
      const layoutWidth = layoutRef.current?.getBoundingClientRect().width ?? 0;
      const sidebarWidth = sidebarRef.current?.getBoundingClientRect().width ?? 0;
      const mainWidth = mainContentRef.current?.getBoundingClientRect().width ?? 0;
      const heroWidth = heroRef.current?.getBoundingClientRect().width ?? 0;
      const overflowDetected = document.documentElement.scrollWidth > document.documentElement.clientWidth;

      console.log('[LAYOUT ROOT WIDTH]', Math.round(layoutWidth));
      console.log('[SIDEBAR WIDTH]', Math.round(sidebarWidth));
      console.log('[MAIN CONTENT WIDTH]', Math.round(mainWidth));
      console.log('[HERO SECTION WIDTH]', Math.round(heroWidth));
      console.log('[OVERFLOW DETECTED]', overflowDetected);
    };

    logLayoutMetrics();
    window.addEventListener('resize', logLayoutMetrics);
    return () => window.removeEventListener('resize', logLayoutMetrics);
  }, [mounted]);

  if (!mounted) return <main className="min-h-screen bg-[#050505]" />;

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
    <main className="relative min-h-screen overflow-hidden bg-[var(--bg-primary)] text-slate-100">
      <div className="ambient-bg" />
      <div ref={layoutRef} className="relative mx-auto grid min-h-screen w-full max-w-[2200px] grid-cols-1 gap-6 overflow-hidden px-6 py-6 xl:grid-cols-[88px_minmax(0,1fr)_420px]">
        <aside ref={sidebarRef} className="panel-premium flex h-full min-h-[90vh] w-[88px] flex-shrink-0 flex-col overflow-hidden p-3">
          <div className="mb-8 grid place-items-center border-b border-white/10 pb-5"><div className="grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br from-cyan-500 to-blue-600">✂</div></div>
          <nav className="flex-1 space-y-2">{navItems.map((item) => <motion.button key={item.label} whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }} transition={springConfigs.snappy} className={`group relative flex w-full items-center justify-center rounded-xl p-3 text-sm ${item.active ? 'bg-cyan-500/15 text-cyan-300' : 'text-slate-400 hover:bg-white/6 hover:text-slate-200'}`}><span>{item.icon}</span><span className="pointer-events-none absolute left-full ml-3 whitespace-nowrap rounded-lg border border-white/10 bg-[#10131c]/95 px-2 py-1 text-xs opacity-0 group-hover:opacity-100">{item.label}</span></motion.button>)}</nav>
        </aside>

        <section ref={mainContentRef} className="min-w-0 space-y-5">
          <header className="panel-premium flex items-center justify-between px-5 py-4">
            <div><p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">Current Sequence</p><h1 className="text-3xl font-semibold tracking-tight">Clipper Launch Campaign</h1></div>
            <div className="flex items-center gap-2"><span className="premium-chip px-3 py-1 text-xs text-cyan-200">AI Online</span><button onClick={handleExport} className="rounded-full bg-white/10 px-4 py-2 text-sm">Render</button><button onClick={handleExport} className="rounded-full bg-gradient-to-r from-cyan-300 to-blue-400 px-4 py-2 text-sm font-semibold text-slate-950">Export</button></div>
          </header>
          <VideoPreview sectionRef={heroRef} />
          <TimelineTracks />
        </section>

        <section className="min-w-0 space-y-5">
          <ClipResultsPanel />
          <InspectorPanel />
        </section>
      </div>
    </main>
  );
}
