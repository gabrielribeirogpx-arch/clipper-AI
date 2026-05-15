'use client';

import dynamic from 'next/dynamic';
import { forwardRef, useEffect, useRef } from 'react';
import { shouldSyncProgress } from '@/lib/playbackEngine';
import { useMounted } from '@/hooks/useMounted';
import { useTimelineStore } from '@/store/timelineStore';

type ReactPlayerHandle = {
  getCurrentTime?: () => number;
  seekTo?: (amount: number, type?: 'seconds' | 'fraction') => void;
};

const ReactPlayerBase = dynamic(() => import('react-player'), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse bg-slate-900" />
});

const ReactPlayer = forwardRef<ReactPlayerHandle, Record<string, unknown>>((props, ref) => (
  <ReactPlayerBase {...props} ref={ref} />
));

ReactPlayer.displayName = 'VideoPreviewReactPlayer';

export function VideoPreview() {
  const { currentTime, setCurrentTime, isPlaying, setPlaying } = useTimelineStore();
  const playerRef = useRef<ReactPlayerHandle | null>(null);
  const mounted = useMounted();

  useEffect(() => {
    if (!mounted) return;
    const playedSeconds = playerRef.current?.getCurrentTime?.() ?? 0;
    if (shouldSyncProgress(currentTime - playedSeconds)) playerRef.current?.seekTo(currentTime, 'seconds');
  }, [currentTime, mounted]);

  return (
    <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-white/5 p-4 shadow-2xl backdrop-blur-xl">
      <div className="aspect-[9/16] overflow-hidden rounded-xl border border-white/10">
        {mounted ? (
          <ReactPlayer
            ref={playerRef}
            url="https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4"
            width="100%"
            height="100%"
            playing={isPlaying}
            controls={false}
            onProgress={(state: { playedSeconds: number }) => setCurrentTime(state.playedSeconds)}
          />
        ) : (
          <div className="h-full w-full animate-pulse bg-slate-900" />
        )}
      </div>
      <div className="mt-3 flex items-center gap-3">
        <button onClick={() => setPlaying(!isPlaying)} className="rounded-lg bg-cyan-400/90 px-3 py-2 text-sm font-semibold text-slate-900 transition hover:scale-[1.03]">
          {isPlaying ? 'Pause' : 'Play'}
        </button>
        <span className="text-xs text-slate-300">{currentTime.toFixed(2)}s</span>
      </div>
    </div>
  );
}
