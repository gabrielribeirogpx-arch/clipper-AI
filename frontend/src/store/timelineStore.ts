'use client';

import { create } from 'zustand';

export type TrackType = 'subtitles' | 'broll' | 'hooks' | 'cuts' | 'effects';

export type BlockStyle = {
  color?: string;
  animation?: 'none' | 'fade' | 'pop' | 'slide';
  zoom?: number;
  emphasis?: 'none' | 'bold' | 'highlight';
};

export type ClipBlock = {
  id: string;
  track: TrackType;
  label: string;
  start: number;
  end: number;
  text?: string;
  style?: BlockStyle;
};

export type RenderJob = {
  id: string;
  clipName: string;
  state: 'queued' | 'rendering' | 'completed' | 'failed';
  progress: number;
};

type TimelineState = {
  videoUrl: string | null;
  duration: number;
  currentTime: number;
  isPlaying: boolean;
  zoom: number;
  selectedBlockId: string | null;
  tracks: Record<TrackType, ClipBlock[]>;
  renderQueue: RenderJob[];
  hydrateFromBackend: () => Promise<void>;
  setCurrentTime: (time: number) => void;
  setPlaying: (playing: boolean) => void;
  setZoom: (zoom: number) => void;
  selectBlock: (id: string | null) => void;
  updateBlock: (track: TrackType, id: string, patch: Partial<ClipBlock>) => void;
  moveBlock: (track: TrackType, id: string, start: number, end: number) => void;
};

const clampTime = (value: number, duration: number) => Math.min(Math.max(value, 0), duration);
const SNAP = 0.1;
const snap = (time: number) => Math.round(time / SNAP) * SNAP;

const tracksSeed: Record<TrackType, ClipBlock[]> = {
  subtitles: [
    { id: 'sub-1', track: 'subtitles', label: 'Abertura', text: 'Gancho inicial com promessa', start: 0, end: 4, style: { animation: 'pop', zoom: 1.1 } },
    { id: 'sub-2', track: 'subtitles', label: 'Valor', text: 'Explica benefício principal', start: 4, end: 10, style: { animation: 'fade', emphasis: 'bold' } }
  ],
  broll: [{ id: 'br-1', track: 'broll', label: 'B-roll Produto', start: 3, end: 8 }],
  hooks: [{ id: 'hk-1', track: 'hooks', label: 'Hook 1', start: 0, end: 2.5 }],
  cuts: [{ id: 'ct-1', track: 'cuts', label: 'Cut A', start: 8, end: 8.2 }],
  effects: [{ id: 'fx-1', track: 'effects', label: 'Glow', start: 1.4, end: 2.2 }]
};

export const useTimelineStore = create<TimelineState>((set, get) => ({
  videoUrl: null,
  duration: 60,
  currentTime: 0,
  isPlaying: false,
  zoom: 1,
  selectedBlockId: 'sub-1',
  tracks: { ...tracksSeed, effects: [] },
  renderQueue: [
    { id: 'job-1', clipName: 'Clip 01', state: 'queued', progress: 0 },
    { id: 'job-2', clipName: 'Clip 02', state: 'rendering', progress: 62 },
    { id: 'job-3', clipName: 'Clip 03', state: 'completed', progress: 100 },
    { id: 'job-4', clipName: 'Clip 04', state: 'failed', progress: 18 }
  ],
  setCurrentTime: (currentTime) => set({ currentTime: clampTime(currentTime, get().duration) }),
  setPlaying: (isPlaying) => set({ isPlaying }),
  setZoom: (zoom) => set({ zoom: Math.min(3, Math.max(0.5, zoom)) }),
  selectBlock: (selectedBlockId) => set({ selectedBlockId }),
  updateBlock: (track, id, patch) =>
    set((state) => ({
      tracks: {
        ...state.tracks,
        [track]: state.tracks[track].map((block) => (block.id === id ? { ...block, ...patch } : block))
      }
    })),
  moveBlock: (track, id, start, end) =>
    set((state) => {
      const moved = state.tracks[track].map((block) => {
        if (block.id !== id) return block;
        const nextStart = snap(clampTime(start, state.duration));
        const nextEnd = snap(clampTime(Math.max(nextStart + 0.1, end), state.duration));
        return { ...block, start: nextStart, end: nextEnd };
      });

      const nextTracks = { ...state.tracks, [track]: moved };
      const payload = {
        subtitles: nextTracks.subtitles,
        broll: nextTracks.broll,
        hooks: nextTracks.hooks,
        cuts: nextTracks.cuts,
      };
      void fetch('http://localhost:8000/timeline/update', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      return { tracks: nextTracks };
    }),
  hydrateFromBackend: async () => {
    const response = await fetch('http://localhost:8000/timeline/render-state');
    const data = await response.json();
    const mapTrack = (items: ClipBlock[] = [], track: TrackType) =>
      items.map((item) => ({ ...item, track }));
    set({
      videoUrl: data.videoUrl ? `http://localhost:8000${data.videoUrl}` : null,
      duration: data.duration ?? 0,
      tracks: {
        subtitles: mapTrack(data.subtitles, 'subtitles'),
        broll: mapTrack(data.broll, 'broll'),
        hooks: mapTrack(data.hooks, 'hooks'),
        cuts: mapTrack(data.cuts, 'cuts'),
        effects: [],
      }
    });
  }
}));
