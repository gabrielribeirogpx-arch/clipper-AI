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
  const color = { queued: 'bg-slate-500', rendering: 'bg-cyan-500', completed: 'bg-emerald-500', failed: 'bg-rose-500' } as const;
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-xl">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-300">Render Queue</h3>
      <div className="space-y-3">{renderQueue.map((job) => <div key={job.id} className="rounded-lg border border-white/10 p-2"><div className="mb-1 flex items-center justify-between text-xs"><span>{job.clipName}</span><span className="capitalize text-slate-300">{job.state}</span></div><div className="h-1.5 rounded bg-slate-800"><div className={`h-1.5 rounded ${color[job.state]}`} style={{ width: `${job.progress}%` }} /></div></div>)}</div>
    </div>
  );
}

export default function Home() {
  const mounted = useMounted();
  if (!mounted) return <main className="min-h-screen bg-[#0B1020]" />;

  return (
    <main className="min-h-screen bg-[#0B1020] text-slate-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_8%_10%,rgba(34,211,238,.16),transparent_35%),radial-gradient(circle_at_80%_8%,rgba(168,85,247,.18),transparent_35%),radial-gradient(circle_at_55%_75%,rgba(56,189,248,.08),transparent_45%)]" />
      <div className="pointer-events-none fixed inset-0 opacity-[0.14] [background-image:radial-gradient(rgba(255,255,255,0.6)_1px,transparent_1px)] [background-size:3px_3px]" />
      <div className="relative mx-auto grid min-h-screen max-w-[1760px] grid-cols-1 gap-6 p-6 xl:grid-cols-[280px_minmax(980px,1fr)]">
        <aside className="rounded-3xl border border-white/10 bg-white/[0.05] p-5 shadow-2xl backdrop-blur-2xl">
          <div className="mb-8 flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-cyan-400 to-violet-500 text-slate-950">✂</div><div><p className="text-sm font-bold tracking-[0.22em] text-cyan-300">CLIPPER AI</p><p className="text-xs text-slate-400">Timeline Studio</p></div></div>
          <nav className="space-y-2">{navItems.map((item) => <motion.button key={item.label} whileHover={{ x: 4 }} className={`flex w-full items-center gap-3 rounded-xl border px-3 py-2.5 text-sm transition-all ${item.active ? 'border-cyan-300/40 bg-cyan-400/10 text-cyan-200 shadow-[0_0_25px_rgba(34,211,238,0.2)]' : 'border-white/5 bg-white/[0.02] text-slate-300 hover:border-white/15 hover:bg-white/[0.06]'}`}><span className="w-4 text-center">{item.icon}</span>{item.label}</motion.button>)}</nav>
        </aside>

        <section className="space-y-6">
          <header className="flex flex-wrap items-center justify-between gap-3 rounded-3xl border border-white/10 bg-[#111827]/70 px-5 py-4 backdrop-blur-2xl">
            <div><p className="text-xs uppercase tracking-[0.18em] text-slate-400">Current Project</p><h1 className="text-xl font-semibold">Clipper Launch Campaign</h1></div>
            <div className="flex items-center gap-3"><span className="rounded-lg border border-violet-400/30 bg-violet-500/15 px-2.5 py-1 text-xs text-violet-200">◍ AI Online</span><span className="rounded-lg border border-cyan-300/30 bg-cyan-500/10 px-2.5 py-1 text-xs text-cyan-200">◔ 78% usage</span><button className="rounded-xl border border-cyan-300/30 bg-cyan-400/15 px-4 py-2 text-sm font-semibold text-cyan-100">Render</button><button className="rounded-xl bg-gradient-to-r from-cyan-400 to-violet-500 px-4 py-2 text-sm font-semibold text-slate-950">↗ Export</button></div>
          </header>
          <div className="grid gap-6 2xl:grid-cols-[minmax(720px,1fr)_320px]"><div className="space-y-6"><VideoPreview /><TimelineTracks /></div><div className="space-y-6"><InspectorPanel /><RenderQueuePanel /></div></div>
        </section>
      </div>
    </main>
  );
}
