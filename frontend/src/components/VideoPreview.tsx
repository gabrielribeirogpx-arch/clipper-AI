'use client';

import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { shouldSyncProgress } from '@/lib/playbackEngine';
import { useMounted } from '@/hooks/useMounted';
import { CaptionPreset, useTimelineStore } from '@/store/timelineStore';

const DEFAULT_VIDEO_URL = 'http://127.0.0.1:8000/media/clip_0.mp4';
const PRESET_STYLES: Record<CaptionPreset, { lineHeight: string; letterSpacing: string; glow: string }> = {
  cinematic: { lineHeight: '1.18', letterSpacing: '0.03em', glow: 'drop-shadow(0 0 22px rgba(80,160,255,.35))' },
  tiktok: { lineHeight: '1.1', letterSpacing: '0.02em', glow: 'drop-shadow(0 0 16px rgba(255,212,0,.28))' },
  hormozi: { lineHeight: '1.05', letterSpacing: '0.015em', glow: 'drop-shadow(0 0 18px rgba(255,122,0,.32))' },
  minimal: { lineHeight: '1.28', letterSpacing: '0.01em', glow: 'drop-shadow(0 0 10px rgba(255,255,255,.2))' },
  neon: { lineHeight: '1.12', letterSpacing: '0.025em', glow: 'drop-shadow(0 0 22px rgba(70,160,255,.55))' },
};

function smartBreak(text: string): string[] {
  const words = text.trim().split(/\s+/).filter(Boolean);
  if (words.length <= 3) return [words.join(' ')];
  const lines: string[] = [];
  let current: string[] = [];
  for (const w of words) {
    current.push(w);
    if (current.length >= 3 || /[,.!?;:]$/.test(w)) {
      lines.push(current.join(' '));
      current = [];
    }
    if (lines.length === 2) break;
  }
  if (current.length > 0 && lines.length < 2) lines.push(current.join(' '));
  return lines.slice(0, 2);
}

export function VideoPreview() {
  const { currentTime, setCurrentTime, isPlaying, setPlaying, duration, videoUrl, tracks } = useTimelineStore();
  const mounted = useMounted();
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const resolvedVideoUrl = videoUrl && videoUrl.trim().length > 0 ? videoUrl : DEFAULT_VIDEO_URL;

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
    console.log(resolvedVideoUrl);
  }, [resolvedVideoUrl]);

  const activeSubtitle = tracks.subtitles.find((block) => currentTime >= block.start && currentTime <= block.end) ?? tracks.subtitles[0];
  const preset = (activeSubtitle?.style?.captionPreset ?? 'cinematic') as CaptionPreset;
  const position = activeSubtitle?.style?.captionPosition ?? 'bottom';
  const heroWord = activeSubtitle?.text?.split(/\s+/).find((word) => word.length > 4) ?? '';
  const lines = smartBreak(activeSubtitle?.text ?? '');

  if (!mounted) return <div className="h-[760px] rounded-[2rem] border border-white/10 bg-white/5" />;

  return (
    <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="relative overflow-hidden rounded-[2.5rem] border border-white/15 bg-[#0d1324]/68 p-12 shadow-[inset_0_1px_0_rgba(255,255,255,.18),0_55px_140px_rgba(0,0,0,.64)] backdrop-blur-3xl">
      <div className="pointer-events-none absolute -left-20 top-4 h-[24rem] w-[24rem] rounded-full bg-cyan-500/30 blur-[130px]" />
      <div className="pointer-events-none absolute -right-20 bottom-0 h-[24rem] w-[24rem] rounded-full bg-violet-500/30 blur-[140px]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_-10%,rgba(255,255,255,.18),transparent_38%),radial-gradient(circle_at_50%_110%,rgba(168,85,247,.24),transparent_48%)]" />

      <div className="relative mx-auto w-full max-w-[1080px]">
        <div className="rounded-[2.3rem] border border-white/20 bg-gradient-to-b from-[#1f2937] to-[#040507] p-4 shadow-[0_0_90px_rgba(34,211,238,.3),0_0_130px_rgba(168,85,247,.22),0_50px_120px_rgba(0,0,0,.7)]">
          <div className="rounded-[1.9rem] border border-white/15 bg-black/95 p-2.5">
            <div className="relative overflow-hidden rounded-[1.5rem] border border-white/10 bg-black">
              <div className="pointer-events-none absolute inset-0 z-20 bg-[linear-gradient(118deg,rgba(255,255,255,0.18)_0%,transparent_30%,transparent_70%,rgba(255,255,255,0.08)_100%)]" />
              <div className="pointer-events-none absolute inset-0 z-10 bg-[radial-gradient(circle_at_50%_0%,rgba(34,211,238,.22),transparent_38%)]" />
              <div className="aspect-video">
                <video
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
                />
                {activeSubtitle?.text && (
                  <div className={`pointer-events-none absolute inset-x-6 z-30 ${position === 'top' ? 'top-[10%]' : position === 'middle' ? 'top-[45%] -translate-y-1/2' : 'bottom-[16%]'}`}>
                    <div className="mx-auto max-w-[78%] rounded-2xl px-6 py-3 text-center" style={{ filter: PRESET_STYLES[preset].glow }}>
                      {lines.map((line, idx) => (
                        <div key={`${line}-${idx}`} className="font-extrabold uppercase text-white" style={{ fontFamily: 'Montserrat, Anton, Arial Black, Arial, sans-serif', fontSize: 'clamp(28px, 3.7vw, 60px)', lineHeight: PRESET_STYLES[preset].lineHeight, letterSpacing: PRESET_STYLES[preset].letterSpacing, textShadow: '0 6px 0 #000, 0 0 28px rgba(0,0,0,.45), 0 0 16px rgba(80,160,255,.28)', animation: 'captionFade 0.2s ease-out' }}>
                          {line.split(' ').map((word) => {
                            const active = heroWord && word.toLowerCase().includes(heroWord.toLowerCase());
                            return <span key={`${line}-${word}`} className={active ? 'animate-pulse' : ''} style={{ color: active ? '#FFD400' : '#FFFFFF', WebkitTextStroke: '2px #000', display: 'inline-block', transform: active ? 'scale(1.15)' : 'scale(1)', transition: 'all 140ms ease-out' }}>{word} </span>;
                          })}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="mt-7 flex items-center gap-5 rounded-[1.3rem] border border-white/10 bg-[#0a1122]/76 px-5 py-4 shadow-[inset_0_1px_0_rgba(255,255,255,.1)] backdrop-blur-xl">
          <button onClick={() => setPlaying(!isPlaying)} className="rounded-xl bg-gradient-to-r from-cyan-300 to-violet-400 px-7 py-3 text-sm font-bold text-slate-950 shadow-[0_0_28px_rgba(34,211,238,.4)]">{isPlaying ? 'Pause' : 'Play'}</button>
          <div className="h-3 flex-1 rounded-full bg-white/10 p-[2px]">
            <div className="h-full rounded-full bg-gradient-to-r from-cyan-300 to-violet-400 shadow-[0_0_24px_rgba(34,211,238,.45)]" style={{ width: `${Math.min((currentTime / Math.max(duration, 0.1)) * 100, 100)}%` }} />
          </div>
          <span className="text-base font-medium text-slate-100">{currentTime.toFixed(2)}s</span>
        </div>
      </div>
      <style jsx global>{`@keyframes captionFade { from { opacity: .55; transform: translateY(10px) scale(.96);} to { opacity: 1; transform: translateY(0) scale(1);} }`} </style>
    </motion.section>
  );
}
