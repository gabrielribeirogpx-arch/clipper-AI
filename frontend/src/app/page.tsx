'use client';

import { motion } from 'framer-motion';
import { InspectorPanel } from '@/components/InspectorPanel';
import { TimelineTracks } from '@/components/TimelineTracks';
import { VideoPreview } from '@/components/VideoPreview';
import { ClipResultsPanel } from '@/components/ClipResultsPanel';
import { useTimelineStore } from '@/store/timelineStore';
import { useMounted } from '@/hooks/useMounted';
import { useEffect } from 'react';

const navItems = [
  { label: 'Projects', icon: '⬢', active: false },
  { label: 'Sequences', icon: '◉', active: false },
  { label: 'Timeline', icon: '▤', active: true },
  { label: 'AI Studio', icon: '✦', active: false },
  { label: 'Assets', icon: '◈', active: false }
];

function RenderQueuePanel() {
  const { renderQueue } = useTimelineStore();
  const color = { queued: 'bg-slate-500', rendering: 'bg-cyan-400', completed: 'bg-emerald-400', failed: 'bg-rose-400' } as const;

  return (
    <div className="rounded-[2.2rem] border border-white/15 bg-white/[0.05] p-7 shadow-[inset_0_1px_0_rgba(255,255,255,0.2),0_24px_80px_rgba(0,0,0,.6)] backdrop-blur-3xl">
      <h3 className="mb-5 text-xs font-semibold uppercase tracking-[0.34em] text-slate-200">Render Queue</h3>
      <div className="space-y-4">
        {renderQueue.map((job) => (
          <div key={job.id} className="rounded-2xl border border-white/10 bg-[#0a1020]/80 p-4">
            <div className="mb-3 flex items-center justify-between text-sm">
              <span className="font-semibold text-slate-100">{job.clipName}</span>
              <span className="capitalize text-slate-300">{job.state}</span>
            </div>
            <div className="h-2.5 rounded-full bg-slate-800/90">
              <div className={`h-2.5 rounded-full shadow-[0_0_18px_rgba(34,211,238,0.45)] ${color[job.state]}`} style={{ width: `${job.progress}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Home() {
  const mounted = useMounted();
  const hydrateFromBackend = useTimelineStore((state) => state.hydrateFromBackend);

  useEffect(() => {
    void hydrateFromBackend();
  }, [hydrateFromBackend]);

  if (!mounted) return <main className="min-h-screen bg-[#05070f]" />;

  const handleExport = async () => {
    try {
      console.log("EXPORT START")

      const response = await fetch("http://localhost:8000/export", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          clip_id: "clip_01"
      }),
    })

      const data = await response.json()

      console.log("EXPORT RESPONSE:", data)

  }   catch (err) {
      console.error("EXPORT ERROR:", err)
  }
}

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#05070f] text-slate-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_8%_10%,rgba(56,189,248,0.24),transparent_34%),radial-gradient(circle_at_90%_12%,rgba(168,85,247,.3),transparent_36%),radial-gradient(circle_at_52%_92%,rgba(34,211,238,.12),transparent_48%),linear-gradient(180deg,#05070f_0%,#070b15_48%,#05070f_100%)]" />
      <div className="pointer-events-none fixed -left-20 top-10 h-[38rem] w-[38rem] rounded-full bg-cyan-500/20 blur-[170px]" />
      <div className="pointer-events-none fixed -right-24 top-10 h-[40rem] w-[40rem] rounded-full bg-violet-500/22 blur-[190px]" />
      <div className="pointer-events-none fixed inset-0 opacity-[0.08] [background-image:radial-gradient(rgba(255,255,255,0.8)_1px,transparent_1px)] [background-size:3px_3px]" />
      <div className="pointer-events-none fixed inset-0 opacity-[0.18]" style={{ background: 'radial-gradient(ellipse_at_center,transparent_34%,rgba(0,0,0,.84)_100%)' }} />

      <div className="relative mx-auto grid min-h-screen max-w-[2200px] grid-cols-1 gap-10 px-10 py-10 2xl:grid-cols-[340px_minmax(1320px,1fr)]">
        <aside className="rounded-[2.4rem] border border-white/15 bg-white/[0.06] p-7 shadow-[inset_0_1px_0_rgba(255,255,255,.2),0_35px_100px_rgba(0,0,0,.55)] backdrop-blur-3xl">
          <div className="mb-14 flex items-center gap-4">
            <div className="grid h-16 w-16 place-items-center rounded-[1.35rem] bg-gradient-to-br from-cyan-300 via-cyan-400 to-violet-500 text-2xl text-slate-950 shadow-[0_0_40px_rgba(34,211,238,0.44)]">✂</div>
            <div>
              <p className="text-base font-bold tracking-[0.24em] text-cyan-200">CLIPPER AI</p>
              <p className="text-sm text-slate-400">Creative Film OS</p>
            </div>
          </div>
          <nav className="space-y-3.5">
            {navItems.map((item) => (
              <motion.button
                key={item.label}
                whileHover={{ x: 10, scale: 1.02, y: -1 }}
                className={`flex w-full items-center gap-4 rounded-2xl border px-4 py-4 text-base transition-all ${item.active
                  ? 'border-cyan-300/45 bg-cyan-400/12 text-cyan-100 shadow-[0_0_28px_rgba(34,211,238,0.26)]'
                  : 'border-white/8 bg-white/[0.03] text-slate-300 hover:border-white/20 hover:bg-white/[0.09] hover:text-slate-100'
                }`}
              >
                <span className="w-6 text-center text-xl">{item.icon}</span>
                <span className="tracking-wide">{item.label}</span>
              </motion.button>
            ))}
          </nav>
        </aside>

        <section className="space-y-10">
          <header className="flex flex-wrap items-center justify-between gap-5 rounded-[2.3rem] border border-white/15 bg-[#0f1628]/75 px-8 py-6 shadow-[inset_0_1px_0_rgba(255,255,255,.16),0_38px_100px_rgba(0,0,0,.5)] backdrop-blur-3xl">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Current Sequence</p>
              <h1 className="text-4xl font-semibold tracking-tight text-white">Clipper Launch Campaign</h1>
            </div>
            <div className="flex items-center gap-3.5">
              <span className="rounded-xl border border-violet-400/30 bg-violet-500/15 px-4 py-2 text-sm text-violet-100">◍ AI Online</span>
              <span className="rounded-xl border border-cyan-300/30 bg-cyan-500/10 px-4 py-2 text-sm text-cyan-100">◔ 78% usage</span>
              <button
                onClick={handleExport}
                className="rounded-xl border border-cyan-300/35 bg-cyan-400/15 px-6 py-3 text-sm font-semibold text-cyan-100">Render</button>
              <button
                onClick={handleExport}
                className="rounded-xl bg-gradient-to-r from-cyan-300 to-violet-500 px-6 py-3 text-sm font-bold text-slate-950 shadow-[0_0_34px_rgba(34,211,238,.35)]"
              >
                ↗ Export
              </button>
            </div>
          </header>

          <div className="grid gap-10 2xl:grid-cols-[minmax(960px,1fr)_420px]">
            <div className="space-y-10">
              <VideoPreview />
              <TimelineTracks />
            </div>
            <div className="space-y-10">
              <ClipResultsPanel />
              <InspectorPanel />
              <RenderQueuePanel />
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
