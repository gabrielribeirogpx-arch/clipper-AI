'use client';

import { motion } from 'framer-motion';
import { springConfigs } from '@/lib/motion-config';

export type WorkspaceKey = 'projects' | 'sequences' | 'timeline' | 'ai-studio' | 'assets';

type WorkspaceContainerProps = {
  workspace: WorkspaceKey;
  onOpenTimeline: () => void;
};

const projects = [
  { name: 'Creator Podcast Ep 204', source: 'Podcast Import', duration: '01:22:19', clipsGenerated: 18, aiStatus: 'Analyzing faces + hooks', modified: '4m ago' },
  { name: 'Livestream Recap - Spring Drop', source: 'Livestream Import', duration: '02:04:11', clipsGenerated: 34, aiStatus: 'Ready for sequencing', modified: '19m ago' },
  { name: 'Agency Client / Q2 Ads', source: 'Upload Batch', duration: '00:37:45', clipsGenerated: 12, aiStatus: 'Rendering social variants', modified: '52m ago' }
];

const clips = [
  { title: 'POV: The One Mistake Founders Repeat', viral: 92, retention: 84, hook: 89, tags: ['Hook', 'Story', 'Founder'] },
  { title: 'This 5s Pattern Doubled Watch Time', viral: 88, retention: 81, hook: 95, tags: ['Retention', 'Tips', 'Editing'] },
  { title: 'Live Reaction That Converted the Chat', viral: 86, retention: 79, hook: 83, tags: ['Livestream', 'Reaction', 'UGC'] }
];

const aiTools = ['AI Hook Generator', 'AI Captions', 'AI Reframing', 'AI Dynamic Zoom', 'AI Meme Detection', 'AI Face Tracking', 'AI Viral Score', 'AI Silence Removal', 'AI Scene Detection', 'AI Emotion Detection'];
const assetGroups = ['Emojis', 'B-roll', 'Sound Effects', 'Transitions', 'Overlays', 'Caption Presets', 'Brand Kits', 'Fonts'];

export function WorkspaceContainer({ workspace, onOpenTimeline }: WorkspaceContainerProps) {
  if (workspace === 'projects') return <ProjectsView onOpenTimeline={onOpenTimeline} />;
  if (workspace === 'sequences') return <SequencesView onOpenTimeline={onOpenTimeline} />;
  if (workspace === 'ai-studio') return <AIStudioView />;
  if (workspace === 'assets') return <AssetsView />;
  return null;
}

export function ProjectsView({ onOpenTimeline }: { onOpenTimeline: () => void }) {
  return <motion.section initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={springConfigs.smooth} className="grid h-full min-h-0 grid-cols-[minmax(0,1fr)_280px] gap-2">
    <div className="panel-premium min-h-0 overflow-y-auto p-4">
      <p className="panel-title">Projects workspace</p>
      <div className="space-y-3">{projects.map((project) => <article key={project.name} className="rounded-2xl border border-white/10 bg-slate-900/40 p-3"><div className="flex gap-3"><div className="h-20 w-36 rounded-xl bg-gradient-to-br from-slate-700 to-slate-900" /><div className="min-w-0 flex-1"><h3 className="truncate text-sm font-semibold">{project.name}</h3><p className="text-xs text-slate-400">{project.source} · {project.duration}</p><div className="mt-2 flex flex-wrap gap-2 text-[11px]"><span className="premium-chip px-2 py-0.5">{project.clipsGenerated} clips</span><span className="premium-chip px-2 py-0.5 text-cyan-200">{project.aiStatus}</span><span className="premium-chip px-2 py-0.5">{project.modified}</span></div></div><button onClick={onOpenTimeline} className="self-start rounded-lg border border-cyan-300/40 bg-cyan-400/15 px-3 py-1 text-xs text-cyan-100">Open editor</button></div></article>)}</div>
    </div>
    <div className="panel-premium p-4"><p className="panel-title">Render history</p><div className="space-y-2 text-xs text-slate-300"><p>• TikTok Batch / 9 clips / Completed</p><p>• Shorts Pack / 6 clips / Processing</p><p>• Reframe 9:16 / 12 clips / Queued</p></div></div>
  </motion.section>;
}

export function SequencesView({ onOpenTimeline }: { onOpenTimeline: () => void }) {
  return <motion.section initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={springConfigs.smooth} className="panel-premium h-full min-h-0 overflow-x-auto p-4"><p className="panel-title">Generated sequences</p><div className="flex h-[calc(100%-1.6rem)] gap-3">{clips.map((clip) => <article key={clip.title} className="group flex h-full w-56 flex-shrink-0 flex-col rounded-2xl border border-white/10 bg-slate-950/60 p-2"><div className="relative flex-1 rounded-xl bg-gradient-to-b from-slate-600 to-black"><div className="absolute inset-0 hidden place-items-center rounded-xl bg-cyan-400/12 text-xs text-cyan-100 group-hover:grid">Autoplay preview</div></div><h3 className="mt-2 line-clamp-2 text-sm">{clip.title}</h3><div className="mt-2 flex gap-1 text-[11px]"><span className="premium-chip px-1.5 py-0.5">Viral {clip.viral}</span><span className="premium-chip px-1.5 py-0.5">Ret {clip.retention}</span><span className="premium-chip px-1.5 py-0.5">Hook {clip.hook}</span></div><div className="mt-2 flex flex-wrap gap-1">{clip.tags.map((tag) => <span key={tag} className="rounded-full border border-white/10 px-2 py-0.5 text-[10px] text-slate-300">{tag}</span>)}</div><div className="mt-2 grid grid-cols-3 gap-1 text-[11px]"><button className="rounded-md border border-white/10 py-1">Queue</button><button className="rounded-md border border-white/10 py-1">Duplicate</button><button onClick={onOpenTimeline} className="rounded-md border border-cyan-300/35 py-1 text-cyan-200">Timeline</button></div></article>)}</div></motion.section>;
}

export function AIStudioView() {
  return <motion.section initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={springConfigs.smooth} className="panel-premium h-full min-h-0 overflow-y-auto p-4"><p className="panel-title">AI studio</p><div className="grid grid-cols-2 gap-2">{aiTools.map((tool) => <div key={tool} className="rounded-xl border border-violet-400/25 bg-gradient-to-br from-violet-400/10 to-cyan-400/5 p-3"><p className="text-sm font-medium">{tool}</p><p className="text-xs text-slate-400">Model ready · GPU accelerated</p></div>)}</div></motion.section>;
}

export function AssetsView() {
  return <motion.section initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={springConfigs.smooth} className="panel-premium h-full min-h-0 overflow-hidden p-4"><div className="mb-3 flex items-center justify-between"><p className="panel-title mb-0">Assets library</p><input placeholder="Search assets..." className="rounded-lg border border-white/10 bg-slate-900/60 px-3 py-1 text-xs" /></div><div className="grid h-[calc(100%-2rem)] grid-cols-4 gap-2 overflow-y-auto">{assetGroups.map((group) => <div key={group} draggable className="rounded-xl border border-white/10 bg-slate-900/50 p-3"><p className="text-xs text-slate-300">{group}</p><p className="text-[11px] text-slate-500">Drag into timeline</p></div>)}</div></motion.section>;
}
