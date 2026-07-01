'use client';

import { useMemo, useRef } from 'react';
import { motion } from 'framer-motion';
import { GeneratedClip, useTimelineStore } from '@/store/timelineStore';
import { desktopBridge } from '@/lib/desktopBridge';
import { mediaUrl } from '@/lib/api';

const formatDuration = (seconds: number) => `${Math.max(0, seconds).toFixed(seconds >= 10 ? 0 : 1)}s`;

const metadataBadge = (clip: GeneratedClip) => {
  if (clip.metadata_status === 'ai') return { label: 'Metadata IA', className: 'border-violet-300/35 bg-violet-400/12 text-violet-100' };
  if (clip.metadata_status === 'pending') return { label: 'Metadata pendente', className: 'border-amber-300/35 bg-amber-400/12 text-amber-100' };
  return { label: 'Sem IA', className: 'border-slate-300/20 bg-slate-400/10 text-slate-200' };
};

const getScoreTone = (score: number) => {
  if (score >= 85) return 'border-emerald-300/35 bg-emerald-400/12 text-emerald-100';
  if (score >= 70) return 'border-cyan-300/30 bg-cyan-400/10 text-cyan-100';
  return 'border-slate-300/20 bg-slate-400/10 text-slate-200';
};

function ViralScoreBadge({ score }: { score: number }) {
  return <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${getScoreTone(score)}`}>Viral {score}</span>;
}

const scoreReason = (clip: GeneratedClip) => {
  const reasons = [];
  if (clip.hook_score) reasons.push(`hook ${clip.hook_score}`);
  if (clip.retention_score) reasons.push(`retenção ${clip.retention_score}`);
  if (clip.emotion_score) reasons.push(`emoção ${clip.emotion_score}`);
  return reasons.length ? `Score baseado em ${reasons.join(', ')}.` : 'Aguardando sinais detalhados da análise.';
};

function ClipCard({ clip, index }: { clip: GeneratedClip; index: number }) {
  const { selectClip, selectedClipId } = useTimelineStore();
  const selected = selectedClipId === clip.id;
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const clipUrl = mediaUrl(clip.final_video);
  const exportedPath = clip.local_export_path || clip.export_path || clip.final_video;
  const downloadTarget = clip.export_path || clipUrl || clip.final_video;
  const title = clip.title || clip.label || `Clip ${index + 1}`;
  const badge = metadataBadge(clip);

  return (
    <motion.article
      whileHover={{ y: -2 }}
      transition={{ type: 'spring', stiffness: 280, damping: 24 }}
      className={`group overflow-hidden rounded-2xl border text-left transition ${selected ? 'border-cyan-300/60 bg-cyan-400/10 shadow-[0_0_0_1px_rgba(34,211,238,.18)]' : 'border-white/10 bg-slate-950/55 hover:border-slate-300/25'}`}
    >
      <button
        onMouseEnter={() => void videoRef.current?.play()}
        onMouseLeave={() => { if (videoRef.current) { videoRef.current.pause(); videoRef.current.currentTime = 0; } }}
        onClick={() => selectClip(clip.id)}
        className="grid w-full grid-cols-[minmax(84px,112px)_minmax(0,1fr)] gap-3 p-3 text-left max-[360px]:grid-cols-1"
      >
        <div className="relative overflow-hidden rounded-xl border border-white/10 bg-black">
          {clipUrl ? <video ref={videoRef} src={clipUrl} muted loop playsInline className="aspect-video h-full w-full object-cover opacity-90 transition group-hover:scale-105" /> : <div className="aspect-video bg-slate-800" />}
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-1.5 text-[10px] text-slate-200">{formatDuration(clip.duration)}</div>
        </div>
        <div className="min-w-0">
          <div className="mb-1.5 flex min-w-0 flex-wrap items-start justify-between gap-2">
            <p className="line-clamp-2 text-sm font-semibold leading-snug text-white">{title}</p>
            <div className="flex shrink-0 flex-row flex-wrap items-end justify-end gap-1">
              <ViralScoreBadge score={clip.viral_score ?? 0} />
              <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${badge.className}`}>{badge.label}</span>
            </div>
          </div>
          <p className="line-clamp-2 text-xs leading-relaxed text-slate-400">{clip.caption || clip.description || 'Sem caption sugerida ainda.'}</p>
          <div className="mt-2 flex flex-wrap gap-1.5 text-[10px] text-slate-300">
            <span className="rounded-full bg-white/6 px-2 py-0.5">Hook {clip.hook_score ?? '—'}</span>
            <span className="rounded-full bg-white/6 px-2 py-0.5">Ret {clip.retention_score ?? '—'}</span>
            <span className="rounded-full bg-white/6 px-2 py-0.5">{clip.start.toFixed(1)}s → {clip.end.toFixed(1)}s</span>
          </div>
        </div>
      </button>
      <div className="border-t border-white/10 bg-black/16 px-3 py-2">
        <p className="mb-2 text-[11px] leading-relaxed text-slate-400">{scoreReason(clip)}</p>
        <div className="grid grid-cols-3 gap-2 text-[11px]">
          <button onClick={() => selectClip(clip.id)} className="rounded-lg border border-cyan-300/25 bg-cyan-300/10 px-2 py-1.5 font-medium text-cyan-100">Aplicar</button>
          <button onClick={() => void desktopBridge.openFolder(exportedPath)} className="rounded-lg border border-white/12 px-2 py-1.5 text-slate-200">Abrir pasta</button>
          <button onClick={() => window.open(downloadTarget, '_blank')} className="rounded-lg border border-emerald-300/25 bg-emerald-300/10 px-2 py-1.5 font-medium text-emerald-100">Baixar</button>
        </div>
      </div>
    </motion.article>
  );
}

export function ClipResultsPanel() {
  const { analysisId, generatedClips, hydrateFromBackend, selectedClipId } = useTimelineStore();
  const clips = useMemo(() => generatedClips, [generatedClips]);
  const bestClip = clips[0];
  const selected = clips.find((clip) => clip.id === selectedClipId) ?? bestClip;

  return (
    <aside className="panel-premium flex min-h-0 flex-col overflow-hidden p-3">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-200/80">AI Assistant</p>
          <h2 className="mt-1 text-base font-semibold text-white">Melhores momentos</h2>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => void hydrateFromBackend(analysisId)} disabled={!analysisId} className="rounded-full border border-cyan-300/25 bg-cyan-300/10 px-2 py-1 text-[10px] font-medium text-cyan-100 disabled:cursor-not-allowed disabled:opacity-40">Atualizar metadata</button>
          <span className="rounded-full border border-white/10 bg-white/[0.04] px-2 py-1 text-[10px] text-slate-300">{clips.length} clips</span>
        </div>
      </div>

      <div className="mb-3 rounded-2xl border border-white/10 bg-slate-950/45 p-3">
        <p className="text-[11px] uppercase tracking-[0.16em] text-slate-400">Sugestão da IA</p>
        <p className="mt-1 line-clamp-2 text-sm font-medium text-slate-100">{selected?.title || selected?.label || 'Importe um vídeo para revelar hooks, cortes e captions.'}</p>
        <p className="mt-2 text-xs leading-relaxed text-slate-400">{selected ? scoreReason(selected) : 'O painel usará dados reais de análise quando disponíveis, sem inventar metadata.'}</p>
      </div>

      <div className="grid min-h-0 flex-1 gap-3 overflow-y-auto pr-1 timeline-scrollbar">
        {clips.map((clip, index) => <ClipCard key={clip.id} clip={clip} index={index} />)}
        {!clips.length && (
          <div className="grid min-h-[260px] place-items-center rounded-2xl border border-dashed border-slate-500/30 bg-slate-950/35 p-5 text-center">
            <div>
              <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-2xl border border-cyan-300/20 bg-cyan-300/10 text-xl">✦</div>
              <p className="text-sm font-semibold text-white">Nenhum clip gerado ainda</p>
              <p className="mt-1 text-xs leading-relaxed text-slate-400">Use Importar ou ingestão YouTube, depois gere clips para ver thumbnails, scores e captions aqui.</p>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
