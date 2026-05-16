'use client';

import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { shouldSyncProgress } from '@/lib/playbackEngine';
import { useMounted } from '@/hooks/useMounted';
import { useTimelineStore } from '@/store/timelineStore';
import { resolveTheme } from '@/caption_themes';

const DEFAULT_VIDEO_URL = 'http://127.0.0.1:8000/media/raw_clip_0.mp4';
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

  const activeSubtitle = tracks.subtitles.find((block) => currentTime >= block.start && currentTime <= block.end);
  const preset = activeSubtitle?.style?.captionPreset ?? 'cinematic';
  const position = activeSubtitle?.style?.captionPosition ?? 'bottom';
  const theme = resolveTheme(preset);
  const lines = theme.splitText(activeSubtitle?.text ?? '');
  const subtitleDuration = Math.max((activeSubtitle?.end ?? 0) - (activeSubtitle?.start ?? 0), 0.01);
  const subtitleProgress = activeSubtitle ? Math.min(Math.max((currentTime - activeSubtitle.start) / subtitleDuration, 0), 0.999) : 0;
  const activeLineIndex = lines.length > 0 ? Math.floor(subtitleProgress * lines.length) : 0;
  const activeLine = lines[activeLineIndex] ?? '';
  const activeLineWords = activeLine.split(/\s+/).filter(Boolean);
  const lineProgress = lines.length > 0 ? (subtitleProgress * lines.length) - activeLineIndex : 0;
  const activeWordIndex = activeLineWords.length > 1
    ? Math.min(Math.floor(Math.max(lineProgress, 0) * activeLineWords.length), activeLineWords.length - 1)
    : 0;

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
                  <div className={`${theme.layout.containerClassName} ${theme.layout.positionClass[position]}`}>
                    <div className={theme.layout.innerClassName} style={{ maxWidth: theme.layout.maxWidth, filter: theme.style.glowFilter }}>
                      <motion.div
                          key={`${activeLine}-${activeLineIndex}`}
                          initial={theme.animation.lineInitial}
                          animate={theme.animation.lineAnimate}
                          transition={theme.animation.lineTransition}
                          className={theme.layout.lineClassName}
                          style={{
                            fontFamily: theme.typography.fontFamily,
                            fontSize: theme.typography.fontSize,
                            fontWeight: theme.typography.fontWeight,
                            lineHeight: theme.typography.lineHeight,
                            letterSpacing: theme.typography.letterSpacing,
                            textTransform: theme.typography.textTransform,
                            textShadow: theme.style.textShadow,
                          }}
                        >
                          {theme.wordTokens(activeLine, activeWordIndex).map((token, tokenIdx) => (
                            <span
                              key={`${activeLine}-${token.text}-${tokenIdx}`}
                              style={{
                                color: token.isHighlighted ? theme.style.highlightedColor : theme.style.baseColor,
                                WebkitTextStroke: theme.style.stroke,
                                background: token.isHighlighted ? theme.style.activeBackgroundBox : theme.style.backgroundBox,
                                borderRadius: '0.2em',
                                padding: token.isHighlighted || theme.style.backgroundBox ? '0.02em 0.16em' : undefined,
                                marginRight: '0.14em',
                                display: 'inline-block',
                                transform: token.isHighlighted ? `scale(${theme.animation.wordActiveScale})` : 'scale(1)',
                                transition: 'transform 120ms ease-out, color 120ms ease-out',
                              }}
                            >
                              {token.text}
                            </span>
                          ))}
                      </motion.div>
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
    </motion.section>
  );
}
