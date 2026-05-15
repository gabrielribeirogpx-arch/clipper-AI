'use client';

import ReactPlayer from 'react-player';
import { useTimelineStore } from '@/store/timelineStore';

export function VideoPreview() {
  const { currentTime, setCurrentTime, isPlaying, setPlaying } = useTimelineStore();

  return (
    <div className="w-full max-w-sm rounded-2xl border border-slate-700 bg-panel p-4 shadow-2xl">
      <div className="aspect-[9/16] overflow-hidden rounded-xl border border-slate-800">
        <ReactPlayer
          url="https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4"
          width="100%"
          height="100%"
          playing={isPlaying}
          controls={false}
          onProgress={(state) => setCurrentTime(state.playedSeconds)}
        />
      </div>
      <div className="mt-3 flex items-center gap-3">
        <button onClick={() => setPlaying(!isPlaying)} className="rounded bg-accent px-3 py-2 text-sm font-semibold">
          {isPlaying ? 'Pause' : 'Play'}
        </button>
        <span className="text-xs text-slate-400">{currentTime.toFixed(1)}s</span>
      </div>
    </div>
  );
}
