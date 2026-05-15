'use client';

import dynamic from 'next/dynamic';
import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { shouldSyncProgress } from '@/lib/playbackEngine';
import { useMounted } from '@/hooks/useMounted';
import { useTimelineStore } from '@/store/timelineStore';

type ReactPlayerHandle = {
  getCurrentTime?: () => number;
  seekTo?: (amount: number, type?: 'seconds' | 'fraction') => void;
};

const ReactPlayer = dynamic(() => import('react-player'), { ssr: false, loading: () => <div className="h-full w-full animate-pulse bg-slate-900" /> });

export function VideoPreview() {
  const { currentTime, setCurrentTime, isPlaying, setPlaying, duration, videoUrl } = useTimelineStore();
  const mounted = useMounted();
  const playerRef = useRef<ReactPlayerHandle | null>(null);

  useEffect(() => {
    if (!mounted) return;
    const playedSeconds = playerRef.current?.getCurrentTime?.() ?? 0;
    if (shouldSyncProgress(currentTime - playedSeconds)) playerRef.current?.seekTo?.(currentTime, 'seconds');
  }, [currentTime, mounted]);

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
                <ReactPlayer
                  ref={undefined}
                  url={videoUrl ?? undefined}
                  width="100%"
                  height="100%"
                  playing={isPlaying}
                  controls={false}
                  onProgress={(state: { playedSeconds: number }) => setCurrentTime(state.playedSeconds)}
                  onReady={(player: ReactPlayerHandle) => {
                    playerRef.current = player;
                  }}
                  onDuration={(value: number) => useTimelineStore.setState({ duration: value })}
                />
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
