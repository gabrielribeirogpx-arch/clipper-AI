'use client';

import { ChangeEvent, DragEvent, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { ingestYouTubeVideo, uploadVideo } from '@/lib/api';
import { useUploadStore } from '@/store/uploadStore';

const PROCESS_STAGES = ['Analyzing speech...', 'Detecting viral hooks...', 'Creating cinematic cuts...', 'Applying reframing...', 'Creating AI timeline...'];
const MAX_SIZE = 1024 * 1024 * 1024;
const MAX_YOUTUBE_DURATION_SECONDS = 6 * 60 * 60;

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

const formatTimestamp = (seconds: number) => {
  const total = Math.floor(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h}h${m}m${s}s`;
  return `${m}m${s}s`;
};

const toHhMmSs = (seconds: number) => {
  const total = Math.floor(seconds);
  const h = String(Math.floor(total / 3600)).padStart(2, '0');
  const m = String(Math.floor((total % 3600) / 60)).padStart(2, '0');
  const s = String(total % 60).padStart(2, '0');
  return `${h}:${m}:${s}`;
};

function YouTubeRangeSelector({
  duration,
  start,
  end,
  onStart,
  onEnd,
}: {
  duration: number;
  start: number;
  end: number;
  onStart: (value: number) => void;
  onEnd: (value: number) => void;
}) {
  const [isDragging, setDragging] = useState<'start' | 'end' | null>(null);
  const startPercent = (start / duration) * 100;
  const endPercent = (end / duration) * 100;

  return (
    <div className="space-y-4 rounded-2xl border border-white/10 bg-[#080f1f]/95 p-4">
      <div className="flex items-center justify-between text-xs uppercase tracking-[0.22em] text-slate-400">
        <span>Selection</span>
        <span>{formatTimestamp(end - start)} window</span>
      </div>
      <div className="relative pt-5">
        <div className="pointer-events-none absolute inset-x-0 top-1/2 h-2 -translate-y-1/2 rounded-full bg-slate-800" />
        <div
          className="pointer-events-none absolute top-1/2 h-2 -translate-y-1/2 rounded-full bg-gradient-to-r from-cyan-400/90 to-violet-400/90 shadow-[0_0_24px_rgba(34,211,238,.45)] transition-all duration-150"
          style={{ left: `${startPercent}%`, width: `${endPercent - startPercent}%` }}
        />
        <input
          type="range"
          min={0}
          max={duration}
          value={start}
          onChange={(e) => onStart(clamp(Number(e.target.value), 0, end - 1))}
          onMouseDown={() => setDragging('start')}
          onMouseUp={() => setDragging(null)}
          onTouchStart={() => setDragging('start')}
          onTouchEnd={() => setDragging(null)}
          className="timeline-thumb pointer-events-auto absolute inset-0 w-full appearance-none bg-transparent"
        />
        <input
          type="range"
          min={0}
          max={duration}
          value={end}
          onChange={(e) => onEnd(clamp(Number(e.target.value), start + 1, duration))}
          onMouseDown={() => setDragging('end')}
          onMouseUp={() => setDragging(null)}
          onTouchStart={() => setDragging('end')}
          onTouchEnd={() => setDragging(null)}
          className="timeline-thumb pointer-events-auto absolute inset-0 w-full appearance-none bg-transparent"
        />
      </div>

      <div className="grid gap-3 text-sm text-slate-100 md:grid-cols-2">
        <div className="rounded-xl border border-cyan-300/30 bg-cyan-300/5 p-3">
          <p className="text-xs uppercase tracking-[0.2em] text-cyan-200">Start</p>
          <p className="mt-1 text-lg font-medium">{formatTimestamp(start)}</p>
          {isDragging === 'start' && <p className="text-xs text-cyan-300">Dragging preview</p>}
        </div>
        <div className="rounded-xl border border-violet-300/30 bg-violet-300/5 p-3">
          <p className="text-xs uppercase tracking-[0.2em] text-violet-200">End</p>
          <p className="mt-1 text-lg font-medium">{formatTimestamp(end)}</p>
          {isDragging === 'end' && <p className="text-xs text-violet-300">Dragging preview</p>}
        </div>
      </div>

      {isDragging && (
        <div className="rounded-xl border border-white/10 bg-slate-900/90 p-3 text-xs text-slate-200">
          Thumbnail preview placeholder • {isDragging === 'start' ? formatTimestamp(start) : formatTimestamp(end)}
        </div>
      )}
    </div>
  );
}

export default function UploadPage() {
  const [isDragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recentUploads, setRecentUploads] = useState<string[]>([]);
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [analysisName, setAnalysisName] = useState('');
  const [startSeconds, setStartSeconds] = useState(0);
  const [endSeconds, setEndSeconds] = useState(MAX_YOUTUBE_DURATION_SECONDS);
  const fileRef = useRef<File | null>(null);
  const router = useRouter();
  const store = useUploadStore();

  const sizeLabel = useMemo(() => (store.uploadedVideo ? `${(store.uploadedVideo.size / (1024 * 1024)).toFixed(1)} MB` : null), [store.uploadedVideo]);
  const validateFile = (file: File) => (['video/mp4', 'video/quicktime'].includes(file.type) ? (file.size > MAX_SIZE ? 'Arquivo maior que 1GB.' : null) : 'Somente MP4 ou MOV.');

  const processFile = async (file: File) => {
    fileRef.current = file;
    const validation = validateFile(file);
    if (validation) return setError(validation);
    setError(null);
    store.setUploadedVideo({ name: file.name, size: file.size, type: file.type, previewUrl: URL.createObjectURL(file) });
    store.setUploadStatus('uploading');
    const result = await uploadVideo(file, analysisName, store.setUploadProgress).catch((e) => {
      store.setUploadStatus('error');
      throw e;
    });
    store.setUploadStatus('processing');
    for (const stage of PROCESS_STAGES) {
      store.setProcessingStage(stage);
      await new Promise((r) => setTimeout(r, 450));
    }
    store.setUploadResult(result.project_id, result.timeline);
    store.setUploadStatus('success');
    setRecentUploads((prev) => [file.name, ...prev].slice(0, 4));
    setTimeout(() => router.push('/editor'), 600);
  };

  const processYoutube = async () => {
    if (!youtubeUrl.trim()) return setError('YouTube URL is required.');
    setError(null);
    store.setUploadStatus('processing');
    const result = await ingestYouTubeVideo({
      youtube_url: youtubeUrl.trim(),
      analysis_name: analysisName.trim() || undefined,
      start_time: toHhMmSs(startSeconds),
      end_time: toHhMmSs(endSeconds),
      min_clip_length: 30,
      max_clip_length: 90,
    });
    for (const stage of PROCESS_STAGES) {
      store.setProcessingStage(stage);
      await new Promise((r) => setTimeout(r, 450));
    }
    store.setUploadResult(result.project_id, result.timeline);
    store.setUploadStatus('success');
    setRecentUploads((prev) => [youtubeUrl, ...prev].slice(0, 4));
    setTimeout(() => router.push('/editor'), 600);
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) void processFile(file).catch((e) => setError(e.message));
  };

  const onFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) void processFile(file).catch((err) => setError(err.message));
  };

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#050813] px-6 py-16 text-white">
      <style jsx>{`
        .timeline-thumb::-webkit-slider-thumb { appearance: none; height: 20px; width: 20px; border-radius: 9999px; background: linear-gradient(130deg, #67e8f9, #a78bfa); box-shadow: 0 0 18px rgba(103, 232, 249, 0.5); cursor: ew-resize; border: 2px solid #0b1220; }
        .timeline-thumb::-moz-range-thumb { height: 20px; width: 20px; border-radius: 9999px; background: linear-gradient(130deg, #67e8f9, #a78bfa); box-shadow: 0 0 18px rgba(103, 232, 249, 0.5); cursor: ew-resize; border: 2px solid #0b1220; }
      `}</style>
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(6,182,212,.25),transparent_36%),radial-gradient(circle_at_80%_15%,rgba(168,85,247,.22),transparent_36%)]" />
      <section className="relative mx-auto max-w-4xl rounded-[2.4rem] border border-white/15 bg-white/[0.04] p-8 shadow-[0_0_120px_rgba(34,211,238,.12)] backdrop-blur-3xl md:p-12">
        <h1 className="text-center text-4xl font-semibold">Upload Cinematic AI</h1>
        <p className="mt-3 text-center text-slate-300">Envie seu vídeo e gere uma timeline inteligente.</p>

        <motion.div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          animate={{ scale: isDragging ? 1.01 : 1, boxShadow: isDragging ? '0 0 50px rgba(34,211,238,.35)' : '0 0 20px rgba(168,85,247,.18)' }}
          className="mt-10 rounded-3xl border border-dashed border-cyan-300/45 bg-[#081025]/70 p-12 text-center"
        >
          <p className="text-lg">Drag & drop MP4/MOV</p>
          <label className="mx-auto mt-8 inline-flex cursor-pointer rounded-xl bg-gradient-to-r from-cyan-300 to-violet-500 px-6 py-3 font-semibold text-slate-950">
            Upload Video
            <input type="file" accept="video/mp4,video/quicktime" className="hidden" onChange={onFileSelect} />
          </label>
        </motion.div>

        <div className="mt-8 grid gap-4 rounded-2xl border border-white/10 bg-white/[0.03] p-5">
          <input value={analysisName} onChange={(e) => setAnalysisName(e.target.value)} placeholder="Nome da análise (opcional)" className="rounded-lg bg-slate-900 px-3 py-2 text-sm" />
          <input value={youtubeUrl} onChange={(e) => setYoutubeUrl(e.target.value)} placeholder="https://youtube.com/live/..." className="rounded-lg bg-slate-900 px-3 py-2 text-sm" />
          <YouTubeRangeSelector duration={MAX_YOUTUBE_DURATION_SECONDS} start={startSeconds} end={endSeconds} onStart={setStartSeconds} onEnd={setEndSeconds} />
          <button onClick={() => void processYoutube().catch((e) => setError(e.message))} className="rounded-xl bg-violet-500 px-4 py-2 text-sm font-semibold transition hover:bg-violet-400">
            Analyze YouTube livestream
          </button>
        </div>

        {store.uploadedVideo && (
          <div className="mt-8 grid gap-4 rounded-2xl border border-white/10 bg-white/[0.03] p-4 md:grid-cols-2">
            <video src={store.uploadedVideo.previewUrl} className="h-52 w-full rounded-xl object-cover" controls />
            <div className="space-y-2 text-sm text-slate-200">
              <p>Arquivo: {store.uploadedVideo.name}</p>
              <p>Tamanho: {sizeLabel}</p>
              <p>Tipo: {store.uploadedVideo.type}</p>
              <p>Status: {store.uploadStatus}</p>
            </div>
          </div>
        )}

        {(store.uploadStatus === 'uploading' || store.uploadStatus === 'processing') && (
          <div className="mt-8 rounded-2xl border border-cyan-300/25 bg-cyan-500/5 p-5">
            <p className="mb-3 text-cyan-100">{store.uploadStatus === 'processing' ? store.processingStage : 'Enviando vídeo...'}</p>
            <div className="h-2 rounded-full bg-slate-800">
              <div className="h-2 rounded-full bg-gradient-to-r from-cyan-300 to-violet-500" style={{ width: `${store.uploadProgress}%` }} />
            </div>
          </div>
        )}

        {error && (
          <p className="mt-5 text-rose-300">
            {error}{' '}
            <button className="underline" onClick={() => fileRef.current && void processFile(fileRef.current).catch((e) => setError(e.message))}>
              Retry
            </button>
          </p>
        )}

        <div className="mt-10">
          <h3 className="text-sm uppercase tracking-[0.2em] text-slate-400">Recent uploads</h3>
          {recentUploads.map((name) => (
            <p key={name} className="mt-2 text-sm text-slate-300">
              • {name}
            </p>
          ))}
        </div>
      </section>
    </main>
  );
}
