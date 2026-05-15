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

  if (!mounted) return <div className="h-[560px] rounded-3xl border border-white/10 bg-white/5" />;

  return (
    <motion.section initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="relative flex justify-center rounded-3xl border border-white/10 bg-[#111827]/55 p-8 shadow-[0_30px_80px_rgba(0,0,0,.6)] backdrop-blur-2xl">
      <div className="absolute inset-0 rounded-3xl bg-[radial-gradient(circle_at_50%_0%,rgba(34,211,238,.15),transparent_50%),radial-gradient(circle_at_50%_100%,rgba(168,85,247,.16),transparent_55%)]" />
      <div className="relative w-full max-w-[420px]">
        <div className="rounded-[28px] border border-cyan-300/25 bg-black p-2 shadow-[0_0_60px_rgba(34,211,238,.25),0_0_70px_rgba(168,85,247,.18)]">
          <div className="relative overflow-hidden rounded-[22px] border border-white/10 bg-black">
            <div className="aspect-[9/16]">
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
        <div className="mt-4 flex items-center gap-3">
          <button onClick={() => setPlaying(!isPlaying)} className="rounded-xl bg-gradient-to-r from-cyan-300 to-violet-400 px-4 py-2 text-sm font-bold text-slate-950">{isPlaying ? 'Pause' : 'Play'}</button>
          <div className="h-2 flex-1 rounded-full bg-white/10">
            <div className="h-full rounded-full bg-gradient-to-r from-cyan-300 to-violet-400" style={{ width: `${Math.min((currentTime / 60) * 100, 100)}%` }} />
          </div>
          <span className="text-xs text-slate-300">{currentTime.toFixed(2)}s</span>
        </div>
      </div>
    </motion.section>
  );
}
