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
  const { currentTime, setCurrentTime, isPlaying, setPlaying } = useTimelineStore();
  const mounted = useMounted();
  const playerRef = useRef<ReactPlayerHandle | null>(null);

  useEffect(() => {
    if (!mounted) return;
    const playedSeconds = playerRef.current?.getCurrentTime?.() ?? 0;
    if (shouldSyncProgress(currentTime - playedSeconds)) playerRef.current?.seekTo?.(currentTime, 'seconds');
  }, [currentTime, mounted]);

  if (!mounted) return <div className="h-[700px] rounded-[2rem] border border-white/10 bg-white/5" />;

  return (
    <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="relative overflow-hidden rounded-[2.25rem] border border-white/15 bg-[#0f172a]/62 p-10 shadow-[inset_0_1px_0_rgba(255,255,255,.16),0_40px_120px_rgba(0,0,0,.58)] backdrop-blur-3xl">
      <div className="pointer-events-none absolute -left-24 top-10 h-72 w-72 rounded-full bg-cyan-500/25 blur-[110px]" />
      <div className="pointer-events-none absolute -right-20 bottom-6 h-72 w-72 rounded-full bg-violet-500/28 blur-[120px]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_2%,rgba(34,211,238,.24),transparent_40%),radial-gradient(circle_at_50%_102%,rgba(168,85,247,.2),transparent_45%)]" />

      <div className="relative mx-auto w-full max-w-[840px]">
        <div className="rounded-[2.2rem] border border-white/20 bg-gradient-to-b from-[#1f2937] to-black p-3 shadow-[0_0_90px_rgba(34,211,238,.24),0_0_120px_rgba(168,85,247,.2)]">
          <div className="rounded-[1.8rem] border border-white/15 bg-black/95 p-2">
            <div className="relative overflow-hidden rounded-[1.35rem] border border-white/10 bg-black">
              <div className="pointer-events-none absolute inset-0 z-10 bg-[linear-gradient(120deg,rgba(255,255,255,0.14)_0%,transparent_28%,transparent_72%,rgba(255,255,255,0.08)_100%)]" />
              <div className="aspect-video">
                <ReactPlayer
                  ref={undefined}
                  url="https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4"
                  width="100%"
                  height="100%"
                  playing={isPlaying}
                  controls={false}
                  onProgress={(state: { playedSeconds: number }) => setCurrentTime(state.playedSeconds)}
                  onReady={(player: ReactPlayerHandle) => {
                    playerRef.current = player;
                  }}
                />
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 flex items-center gap-4 rounded-2xl border border-white/10 bg-[#0b1224]/75 px-4 py-3 backdrop-blur-xl">
          <button onClick={() => setPlaying(!isPlaying)} className="rounded-xl bg-gradient-to-r from-cyan-300 to-violet-400 px-6 py-2.5 text-sm font-bold text-slate-950 shadow-[0_0_22px_rgba(34,211,238,.35)]">{isPlaying ? 'Pause' : 'Play'}</button>
          <div className="h-2.5 flex-1 rounded-full bg-white/10">
            <div className="h-full rounded-full bg-gradient-to-r from-cyan-300 to-violet-400" style={{ width: `${Math.min((currentTime / 60) * 100, 100)}%` }} />
          </div>
          <span className="text-sm font-medium text-slate-200">{currentTime.toFixed(2)}s</span>
        </div>
      </div>
    </motion.section>
  );
}
