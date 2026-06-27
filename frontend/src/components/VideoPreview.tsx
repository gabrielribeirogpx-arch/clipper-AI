'use client';

import { type RefObject, useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { shouldSyncProgress } from '@/lib/playbackEngine';
import { useMounted } from '@/hooks/useMounted';
import { useTimelineStore } from '@/store/timelineStore';


export function VideoPreview({ sectionRef }: { sectionRef?: RefObject<HTMLElement | null> }) {
  const { currentTime, setCurrentTime, isPlaying, setPlaying, duration, videoUrl, clipRenderMode, setClipRenderMode, dualRegions, setDualRegions } = useTimelineStore();
  const [dragging, setDragging] = useState<'regionA' | 'regionB' | null>(null);
  const mounted = useMounted();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const isRegionSetup = process.env.NEXT_PUBLIC_REGION_SETUP === 'true';

  const resolvedVideoUrl = videoUrl && videoUrl.trim().length > 0 ? videoUrl : null;

  useEffect(() => {
    if (!mounted || !videoRef.current) return;
    const video = videoRef.current;
    const drift = currentTime - video.currentTime;
    if (shouldSyncProgress(drift)) video.currentTime = currentTime;
  }, [currentTime, mounted]);

  useEffect(() => {
    if (!mounted || !videoRef.current) return;
    const video = videoRef.current;
    video.volume = 1;
    if (isPlaying) {
      void video.play();
      return;
    }
    video.pause();
  }, [isPlaying, mounted]);

  useEffect(() => {
    if (!mounted || !videoRef.current) return;
    videoRef.current.load();
  }, [resolvedVideoUrl, mounted]);

  useEffect(() => {
    if (!mounted || !videoRef.current || !isPlaying) return;
    let frameId = 0;
    const syncFrame = () => {
      const video = videoRef.current;
      if (!video) return;
      setCurrentTime(video.currentTime);
      frameId = requestAnimationFrame(syncFrame);
    };
    frameId = requestAnimationFrame(syncFrame);
    return () => cancelAnimationFrame(frameId);
  }, [isPlaying, mounted, setCurrentTime]);

  useEffect(() => {
    console.log(resolvedVideoUrl);
  }, [resolvedVideoUrl]);


  useEffect(() => {
    console.log('[FINAL CINEMATIC POLISH ACTIVE]');
    console.log('[PLAYER SIDE PADDING REDUCED]');
    console.log('[EMPTY STATE CENTERED]');
    console.log('[PREMIUM VISUAL BALANCE COMPLETE]');
  }, []);

  useEffect(() => {
    if (isRegionSetup) {
      console.log('[REGION SETUP OVERLAY ENABLED]');
      return;
    }
    console.log('[EDITOR OVERLAY DISABLED]');
  }, [isRegionSetup]);


  if (!mounted) return <div className="editor-player-card rounded-[2rem] border border-white/10 bg-white/5" />;

  return (
    <motion.section ref={sectionRef} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="panel-premium editor-player-card relative w-full p-2">
      <div className="pointer-events-none absolute inset-0"><div className="absolute -left-20 top-4 h-[24rem] w-[24rem] rounded-full bg-cyan-500/30 blur-[130px]" /></div>
      <div className="pointer-events-none absolute inset-0"><div className="absolute -right-20 bottom-0 h-[24rem] w-[24rem] rounded-full bg-violet-500/30 blur-[140px]" /></div>
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_-10%,rgba(255,255,255,.12),transparent_38%)]" />

      <div className="editor-video-area relative">
        <div className="editor-video-frame rounded-[14px] border border-slate-400/16 bg-gradient-to-b from-[#0c1222] to-[#05070d] p-[0.28rem] shadow-[0_24px_70px_rgba(0,0,0,.72)]">
          <div className="mb-1 flex items-center justify-start gap-1.5">
            <div className="flex gap-2">
            <button className={`rounded-lg px-2.5 py-0.5 text-xs ${clipRenderMode === 'ai_tracking' ? 'bg-cyan-400 text-black' : 'bg-white/10'}`} onClick={() => setClipRenderMode('ai_tracking')}>AI Tracking</button>
            <button className={`rounded-lg px-2.5 py-0.5 text-xs ${clipRenderMode === 'dual_region' ? 'bg-cyan-400 text-black' : 'bg-white/10'}`} onClick={() => setClipRenderMode('dual_region')}>Dual Region</button>
          </div>
          </div>
          <div className="rounded-[12px] border border-white/10 bg-black/95 p-[0.35rem]">
            <div className="relative overflow-hidden rounded-[1rem] border border-white/10 bg-black">
              <div className="pointer-events-none absolute inset-0 z-20 bg-[linear-gradient(118deg,rgba(255,255,255,0.18)_0%,transparent_30%,transparent_70%,rgba(255,255,255,0.08)_100%)]" />
              <div className="pointer-events-none absolute inset-0 z-10 bg-[radial-gradient(circle_at_50%_0%,rgba(34,211,238,.22),transparent_38%)]" />
              <div className="relative w-full" style={{ aspectRatio: '16 / 9' }}>
                {resolvedVideoUrl ? (<video
                  key={resolvedVideoUrl}
                  ref={videoRef}
                  src={resolvedVideoUrl}
                  controls
                  playsInline
                  preload="auto"
                  crossOrigin="anonymous"
                  className="h-full w-full object-contain"
                  onLoadedMetadata={() => {
                    console.log('VIDEO METADATA LOADED');
                    if (videoRef.current) {
                      videoRef.current.volume = 1;
                      useTimelineStore.setState({ duration: videoRef.current.duration || 0 });
                    }
                  }}
                  onCanPlay={() => {
                    console.log('VIDEO READY');
                  }}
                  onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
                />) : (<div className="grid h-full w-full place-items-center text-slate-300"><div className="text-center"><p className="text-sm font-medium">Nenhum clip real disponível ainda.</p><p className="mt-1 text-xs text-slate-400">Faça upload ou gere clips com IA para começar.</p></div></div>)}
                {clipRenderMode === 'dual_region' && isRegionSetup === true && (
                  <div
                    className="absolute inset-0 z-30"
                    onMouseMove={(e) => {
                      if (!dragging) return;
                      const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
                      const x = ((e.clientX - rect.left) / rect.width) * 1920;
                      const y = ((e.clientY - rect.top) / rect.height) * 1080;
                      const region = dualRegions[dragging];
                      setDualRegions({ ...dualRegions, [dragging]: { ...region, x: Math.max(0, Math.min(1920 - region.width, x - region.width / 2)), y: Math.max(0, Math.min(1080 - region.height, y - region.height / 2)) } });
                    }}
                    onMouseUp={() => setDragging(null)}
                  >
                    {(['regionA', 'regionB'] as const).map((key) => {
                      const r = dualRegions[key];
                      return <div key={key} onMouseDown={() => setDragging(key)} className={`absolute border-2 ${key === 'regionA' ? 'border-cyan-300 bg-cyan-300/20' : 'border-violet-300 bg-violet-300/20'}`} style={{ left: `${(r.x / 1920) * 100}%`, top: `${(r.y / 1080) * 100}%`, width: `${(r.width / 1920) * 100}%`, height: `${(r.height / 1080) * 100}%` }} />;
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
        {clipRenderMode === 'dual_region' && isRegionSetup === true && <div className="mt-3 flex gap-2 text-xs">
          <button className="rounded bg-white/10 px-2 py-1" onClick={() => setDualRegions({ regionA: { x: 120, y: 80, width: 1680, height: 460 }, regionB: { x: 120, y: 540, width: 1680, height: 460 } })}>Podcast Split</button>
          <button className="rounded bg-white/10 px-2 py-1" onClick={() => setDualRegions({ regionA: { x: 0, y: 0, width: 700, height: 500 }, regionB: { x: 640, y: 0, width: 1280, height: 720 } })}>Facecam + Gameplay</button>
          <button className="rounded bg-white/10 px-2 py-1" onClick={() => setDualRegions({ regionA: { x: 0, y: 0, width: 960, height: 540 }, regionB: { x: 960, y: 0, width: 960, height: 540 } })}>Debate</button>
          <button className="rounded bg-white/10 px-2 py-1" onClick={() => setDualRegions({ regionA: { x: 120, y: 120, width: 1680, height: 420 }, regionB: { x: 120, y: 580, width: 1680, height: 420 } })}>Reaction</button>
        </div>}

        <div className="editor-player-controls mt-1 flex items-center gap-2 rounded-[10px] border border-white/10 bg-[#0a1122]/82 px-2 py-1.5 shadow-[inset_0_1px_0_rgba(255,255,255,.1)] backdrop-blur-xl">
          <button onClick={() => setPlaying(!isPlaying)} className="rounded-md bg-cyan-300 px-3 py-1 text-[11px] font-bold text-slate-950">{isPlaying ? 'Pause' : 'Play'}</button>
          <div className="h-2 flex-1 rounded-full bg-white/10 p-[2px]">
            <div className="h-full rounded-full bg-gradient-to-r from-cyan-300 to-violet-400 shadow-[0_0_24px_rgba(34,211,238,.45)]" style={{ width: `${Math.min((currentTime / Math.max(duration, 0.1)) * 100, 100)}%` }} />
          </div>
          <span className="text-xs font-medium text-slate-100">{currentTime.toFixed(2)}s</span>
        </div>
      </div>
    </motion.section>
  );
}
