'use client';

import { ChangeEvent, DragEvent, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { uploadVideo } from '@/lib/api';
import { useUploadStore } from '@/store/uploadStore';

const PROCESS_STAGES = ['Analyzing speech...', 'Detecting viral hooks...', 'Creating cinematic cuts...', 'Applying reframing...', 'Creating AI timeline...'];
const MAX_SIZE = 1024 * 1024 * 1024;

export default function UploadPage() {
  const [isDragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recentUploads, setRecentUploads] = useState<string[]>([]);
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
    const result = await uploadVideo(file, store.setUploadProgress).catch((e) => {
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

  return <main className="relative min-h-screen overflow-hidden bg-[#050813] px-6 py-16 text-white"><div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(6,182,212,.25),transparent_36%),radial-gradient(circle_at_80%_15%,rgba(168,85,247,.22),transparent_36%)]"/><section className="relative mx-auto max-w-4xl rounded-[2.4rem] border border-white/15 bg-white/[0.04] p-8 shadow-[0_0_120px_rgba(34,211,238,.12)] backdrop-blur-3xl md:p-12"><h1 className="text-center text-4xl font-semibold">Upload Cinematic AI</h1><p className="mt-3 text-center text-slate-300">Envie seu vídeo e gere uma timeline inteligente.</p><motion.div onDragOver={(e)=>{e.preventDefault();setDragging(true);}} onDragLeave={()=>setDragging(false)} onDrop={onDrop} animate={{scale:isDragging?1.01:1, boxShadow:isDragging?'0 0 50px rgba(34,211,238,.35)':'0 0 20px rgba(168,85,247,.18)'}} className="mt-10 rounded-3xl border border-dashed border-cyan-300/45 bg-[#081025]/70 p-12 text-center"><p className="text-lg">Drag & drop MP4/MOV</p><label className="mx-auto mt-8 inline-flex cursor-pointer rounded-xl bg-gradient-to-r from-cyan-300 to-violet-500 px-6 py-3 font-semibold text-slate-950">Upload Video<input type="file" accept="video/mp4,video/quicktime" className="hidden" onChange={onFileSelect} /></label></motion.div>{store.uploadedVideo && <div className="mt-8 grid gap-4 rounded-2xl border border-white/10 bg-white/[0.03] p-4 md:grid-cols-2"><video src={store.uploadedVideo.previewUrl} className="h-52 w-full rounded-xl object-cover" controls /><div className="space-y-2 text-sm text-slate-200"><p>Arquivo: {store.uploadedVideo.name}</p><p>Tamanho: {sizeLabel}</p><p>Tipo: {store.uploadedVideo.type}</p><p>Status: {store.uploadStatus}</p></div></div>}{(store.uploadStatus==='uploading'||store.uploadStatus==='processing')&&<div className="mt-8 rounded-2xl border border-cyan-300/25 bg-cyan-500/5 p-5"><p className="mb-3 text-cyan-100">{store.uploadStatus==='processing'?store.processingStage:'Enviando vídeo...'}</p><div className="h-2 rounded-full bg-slate-800"><div className="h-2 rounded-full bg-gradient-to-r from-cyan-300 to-violet-500" style={{width:`${store.uploadProgress}%`}}/></div></div>}{error && <p className="mt-5 text-rose-300">{error} <button className="underline" onClick={() => fileRef.current && void processFile(fileRef.current).catch((e)=>setError(e.message))}>Retry</button></p>}<div className="mt-10"><h3 className="text-sm uppercase tracking-[0.2em] text-slate-400">Recent uploads</h3>{recentUploads.map((name)=><p key={name} className="mt-2 text-sm text-slate-300">• {name}</p>)}</div></section></main>;
}
