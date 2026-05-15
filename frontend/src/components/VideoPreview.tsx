"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef } from "react";
import { shouldSyncProgress } from "@/lib/playbackEngine";
import { useMounted } from "@/hooks/useMounted";
import { useTimelineStore } from "@/store/timelineStore";

type ReactPlayerHandle = {
  getCurrentTime?: () => number;
  seekTo?: (
    amount: number,
    type?: "seconds" | "fraction"
  ) => void;
};

const ReactPlayer = dynamic(() => import("react-player"), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full animate-pulse bg-slate-900" />
  ),
});

export function VideoPreview() {
  const {
    currentTime,
    setCurrentTime,
    isPlaying,
    setPlaying,
  } = useTimelineStore();

  const mounted = useMounted();

  const playerRef = useRef<ReactPlayerHandle | null>(null);

  useEffect(() => {
    if (!mounted) return;

    const playedSeconds =
      playerRef.current?.getCurrentTime?.() ?? 0;

    if (
      shouldSyncProgress(currentTime - playedSeconds)
    ) {
      playerRef.current?.seekTo?.(
        currentTime,
        "seconds"
      );
    }
  }, [currentTime, mounted]);

  if (!mounted) {
    return (
      <div className="w-full max-w-sm rounded-3xl border border-white/10 bg-white/5 p-4 shadow-2xl backdrop-blur-xl">
        <div className="aspect-[9/16] overflow-hidden rounded-2xl bg-slate-900 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="w-full max-w-sm rounded-3xl border border-white/10 bg-gradient-to-b from-[#111827]/95 to-[#0B1020]/95 p-4 shadow-[0_0_60px_rgba(0,255,255,0.08)] backdrop-blur-2xl">
      
      <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-black">
        
        <div className="absolute inset-0 z-10 pointer-events-none bg-gradient-to-t from-black/40 via-transparent to-transparent" />

        <div className="aspect-[9/16]">
          <ReactPlayer
            ref={undefined}
            url="https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4"
            width="100%"
            height="100%"
            playing={isPlaying}
            controls={false}
            muted={false}
            onProgress={(state: { playedSeconds: number }) => {
              setCurrentTime(state.playedSeconds);
            }}
            onReady={(player: ReactPlayerHandle) => {
              playerRef.current = player;
            }}
          />
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between gap-3">
        
        <button
          onClick={() => setPlaying(!isPlaying)}
          className="rounded-xl bg-cyan-400 px-4 py-2 text-sm font-bold text-slate-900 transition-all duration-200 hover:scale-[1.03] hover:bg-cyan-300 active:scale-[0.98]"
        >
          {isPlaying ? "Pause" : "Play"}
        </button>

        <div className="flex-1">
          <div className="h-2 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-blue-500 transition-all duration-150"
              style={{
                width: `${Math.min(
                  (currentTime / 60) * 100,
                  100
                )}%`,
              }}
            />
          </div>
        </div>

        <span className="min-w-[60px] text-right text-xs font-medium text-slate-300">
          {currentTime.toFixed(2)}s
        </span>
      </div>
    </div>
  );
}