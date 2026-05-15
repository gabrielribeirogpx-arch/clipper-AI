'use client';

import { motion } from 'framer-motion';
import { InspectorPanel } from '@/components/InspectorPanel';
import { TimelineTracks } from '@/components/TimelineTracks';
import { VideoPreview } from '@/components/VideoPreview';
import { useTimelineStore } from '@/store/timelineStore';
import { useMounted } from '@/hooks/useMounted';

const navItems = [
  { label: 'Projects', icon: '▦', active: false },
  { label: 'Clips', icon: '◉', active: false },
  { label: 'Timeline', icon: '▤', active: true },
  { label: 'AI Tools', icon: '✦', active: false },
  { label: 'Assets', icon: '◈', active: false }
];

function RenderQueuePanel() {
  const { renderQueue } = useTimelineStore();
  const color = { queued: 'bg-slate-500', rendering: 'bg-cyan-400', completed: 'bg-emerald-400', failed: 'bg-rose-400' } as const;

  return (
    <div className="rounded-[2rem] border border-white/15 bg-white/[0.06] p-6 shadow-[inset_0_1px_0_rgba(255,255,255,0.15),0_25px_80px_rgba(0,0,0,.45)] backdrop-blur-3xl">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-[0.24em] text-slate-200">Render Queue</h3>
      <div className="space-y-4">
        {renderQueue.map((job) => (
          <div key={job.id} className="rounded-2xl border border-white/10 bg-[#0b1224]/80 p-3.5">
            <div className="mb-2 flex items-center justify-between text-sm">
              <span className="font-medium text-slate-100">{job.clipName}</span>
              <span className="capitalize text-slate-300">{job.state}</span>
            </div>
            <div className="h-2 rounded-full bg-slate-800/90">
              <div className={`h-2 rounded-full ${color[job.state]}`} style={{ width: `${job.progress}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Home() {
  const mounted = useMounted();
  if (!mounted) return <main className="min-h-screen bg-[#070a15]" />;

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#070a15] text-slate-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_8%_8%,rgba(34,211,238,.28),transparent_28%),radial-gradient(circle_at_90%_14%,rgba(168,85,247,.34),transparent_34%),radial-gradient(circle_at_52%_88%,rgba(56,189,248,.14),transparent_44%),linear-gradient(180deg,#060910_0%,#090d1a_45%,#070a14_100%)]" />
      <div className="pointer-events-none fixed -left-24 top-24 h-[32rem] w-[32rem] rounded-full bg-cyan-500/20 blur-[140px]" />
      <div className="pointer-events-none fixed -right-28 top-16 h-[34rem] w-[34rem] rounded-full bg-violet-500/20 blur-[150px]" />
      <div className="pointer-events-none fixed inset-0 opacity-[0.1] [background-image:radial-gradient(rgba(255,255,255,0.7)_1px,transparent_1px)] [background-size:3px_3px]" />
      <div className="pointer-events-none fixed inset-0 opacity-[0.14]" style={{ background: 'radial-gradient(ellipse_at_center,transparent_38%,rgba(0,0,0,.72)_100%)' }} />

      <div className="relative mx-auto grid min-h-screen max-w-[1980px] grid-cols-1 gap-8 px-8 py-8 2xl:grid-cols-[360px_minmax(1120px,1fr)]">
        <aside className="rounded-[2.25rem] border border-white/15 bg-white/[0.06] p-6 shadow-[inset_0_1px_0_rgba(255,255,255,.18),0_40px_100px_rgba(0,0,0,.45)] backdrop-blur-3xl">
          <div className="mb-10 flex items-center gap-4">
            <div className="grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-cyan-300 via-cyan-400 to-violet-500 text-xl text-slate-950 shadow-[0_0_35px_rgba(34,211,238,0.38)]">✂</div>
            <div>
              <p className="text-base font-bold tracking-[0.22em] text-cyan-200">CLIPPER AI</p>
              <p className="text-sm text-slate-400">Cinematic Editing Suite</p>
            </div>
          </div>
          <nav className="space-y-3">
            {navItems.map((item) => (
              <motion.button
                key={item.label}
                whileHover={{ x: 8, scale: 1.015 }}
                className={`flex w-full items-center gap-4 rounded-2xl border px-4 py-3.5 text-base transition-all ${item.active
                    ? 'border-cyan-300/45 bg-cyan-400/12 text-cyan-100 shadow-[0_0_28px_rgba(34,211,238,0.26)]'
                    : 'border-white/8 bg-white/[0.03] text-slate-300 hover:border-white/20 hover:bg-white/[0.08] hover:text-slate-100'
                  }`}
              >
                <span className="w-6 text-center text-lg">{item.icon}</span>
                <span className="tracking-wide">{item.label}</span>
              </motion.button>
            ))}
          </nav>
        </aside>

        <section className="space-y-8">
          <header className="flex flex-wrap items-center justify-between gap-4 rounded-[2rem] border border-white/15 bg-[#10192d]/70 px-7 py-5 shadow-[inset_0_1px_0_rgba(255,255,255,.12),0_35px_90px_rgba(0,0,0,.45)] backdrop-blur-3xl">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Current Project</p>
              <h1 className="text-3xl font-semibold tracking-tight">Clipper Launch Campaign</h1>
            </div>
            <div className="flex items-center gap-3">
              <span className="rounded-xl border border-violet-400/30 bg-violet-500/15 px-3 py-1.5 text-sm text-violet-100">◍ AI Online</span>
              <span className="rounded-xl border border-cyan-300/30 bg-cyan-500/10 px-3 py-1.5 text-sm text-cyan-100">◔ 78% usage</span>
              <button className="rounded-xl border border-cyan-300/35 bg-cyan-400/15 px-5 py-2.5 text-sm font-semibold text-cyan-100">Render</button>
              <button className="rounded-xl bg-gradient-to-r from-cyan-300 to-violet-500 px-5 py-2.5 text-sm font-bold text-slate-950 shadow-[0_0_30px_rgba(34,211,238,.35)]">↗ Export</button>
            </div>
          </header>

          <div className="grid gap-8 2xl:grid-cols-[minmax(820px,1fr)_380px]">
            <div className="space-y-8">
              <VideoPreview />
              <TimelineTracks />
            </div>
            <div className="space-y-8">
              <InspectorPanel />
              <RenderQueuePanel />
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
