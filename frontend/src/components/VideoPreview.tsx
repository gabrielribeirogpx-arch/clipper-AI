'use client';

import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { shouldSyncProgress } from '@/lib/playbackEngine';
import { useMounted } from '@/hooks/useMounted';
import { useTimelineStore } from '@/store/timelineStore';


export function VideoPreview() {
  const { currentTime, setCurrentTime, isPlaying, setPlaying, duration, videoUrl, clipRenderMode, setClipRenderMode, dualRegions, setDualRegions } = useTimelineStore();
  const [dragging, setDragging] = useState<'regionA' | 'regionB' | null>(null);
  const mounted = useMounted();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const isRegionSetup = false;

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
    if (isRegionSetup) {
      console.log('[REGION SETUP OVERLAY ENABLED]');
      return;
    }
    console.log('[EDITOR OVERLAY DISABLED]');
  }, [isRegionSetup]);

  if (!mounted) return <div className="h-[760px] rounded-[2rem] border border-white/10 bg-white/5" />;

  return (
    <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="relative overflow-hidden rounded-[2.5rem] border border-white/15 bg-[#0d1324]/68 p-12 shadow-[inset_0_1px_0_rgba(255,255,255,.18),0_55px_140px_rgba(0,0,0,.64)] backdrop-blur-3xl">
      <div className="pointer-events-none absolute -left-20 top-4 h-[24rem] w-[24rem] rounded-full bg-cyan-500/30 blur-[130px]" />
      <div className="pointer-events-none absolute -right-20 bottom-0 h-[24rem] w-[24rem] rounded-full bg-violet-500/30 blur-[140px]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_-10%,rgba(255,255,255,.18),transparent_38%),radial-gradient(circle_at_50%_110%,rgba(168,85,247,.24),transparent_48%)]" />

      <div className="relative mx-auto w-full max-w-[1080px]">
        <div className="rounded-[2.3rem] border border-white/20 bg-gradient-to-b from-[#1f2937] to-[#040507] p-4 shadow-[0_0_90px_rgba(34,211,238,.3),0_0_130px_rgba(168,85,247,.22),0_50px_120px_rgba(0,0,0,.7)]">
          <div className="mb-3 flex gap-2">
            <button className={`rounded-lg px-3 py-1 text-sm ${clipRenderMode === 'ai_tracking' ? 'bg-cyan-400 text-black' : 'bg-white/10'}`} onClick={() => setClipRenderMode('ai_tracking')}>AI Tracking</button>
            <button className={`rounded-lg px-3 py-1 text-sm ${clipRenderMode === 'dual_region' ? 'bg-cyan-400 text-black' : 'bg-white/10'}`} onClick={() => setClipRenderMode('dual_region')}>Dual Region</button>
          </div>
          <div className="rounded-[1.9rem] border border-white/15 bg-black/95 p-2.5">
            <div className="relative overflow-hidden rounded-[1.5rem] border border-white/10 bg-black">
              <div className="pointer-events-none absolute inset-0 z-20 bg-[linear-gradient(118deg,rgba(255,255,255,0.18)_0%,transparent_30%,transparent_70%,rgba(255,255,255,0.08)_100%)]" />
              <div className="pointer-events-none absolute inset-0 z-10 bg-[radial-gradient(circle_at_50%_0%,rgba(34,211,238,.22),transparent_38%)]" />
              <div className="aspect-video relative">
                {resolvedVideoUrl ? (<video
                  key={resolvedVideoUrl}
                  ref={videoRef}
                  src={resolvedVideoUrl}
                  controls
                  playsInline
                  preload="auto"
                  crossOrigin="anonymous"
                  className="h-full w-full"
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
                />) : (<div className="flex h-full items-center justify-center text-slate-300">Nenhum clip real disponível ainda.</div>)}
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

        <div className="mt-7 flex items-center gap-5 rounded-[1.3rem] border border-white/10 bg-[#0a1122]/76 px-5 py-4 shadow-[inset_0_1px_0_rgba(255,255,255,.1)] backdrop-blur-xl">
          <button onClick={() => setPlaying(!isPlaying)} className="rounded-xl bg-gradient-to-r from-cyan-300 to-violet-400 px-7 py-3 text-sm font-bold text-slate-950 shadow-[0_0_28px_rgba(34,211,238,.4)]">{isPlaying ? 'Pause' : 'Play'}</button>
          <div className="h-3 flex-1 rounded-full bg-white/10 p-[2px]">
            <div className="h-full rounded-full bg-gradient-to-r from-cyan-300 to-violet-400 shadow-[0_0_24px_rgba(34,211,238,.45)]" style={{ width: `${Math.min((currentTime / Math.max(duration, 0.1)) * 100, 100)}%` }} />
          </div>
          <span className="text-base font-medium text-slate-100">{currentTime.toFixed(2)}s</span>
        </div>
      </div>
    </motion.section>
  );
}
