'use client';

import { create } from 'zustand';

type ClipBlock = { id: string; label: string; start: number; end: number; text?: string };

type TimelineState = {
  duration: number;
  currentTime: number;
  isPlaying: boolean;
  subtitles: ClipBlock[];
  broll: ClipBlock[];
  hooks: ClipBlock[];
  cuts: ClipBlock[];
  setCurrentTime: (time: number) => void;
  setPlaying: (playing: boolean) => void;
  updateBlock: (track: 'subtitles' | 'broll' | 'hooks' | 'cuts', id: string, patch: Partial<ClipBlock>) => void;
};

const seed = {
  duration: 60,
  currentTime: 0,
  isPlaying: false,
  subtitles: [
    { id: 'sub-1', label: 'Abertura', text: 'Gancho inicial com promessa', start: 0, end: 4 },
    { id: 'sub-2', label: 'Valor', text: 'Explica benefício principal', start: 4, end: 10 }
  ],
  broll: [{ id: 'br-1', label: 'B-roll Produto', start: 3, end: 8 }],
  hooks: [{ id: 'hk-1', label: 'Hook 1', start: 0, end: 2.5 }],
  cuts: [{ id: 'ct-1', label: 'Cut A', start: 8, end: 8.2 }]
};

export const useTimelineStore = create<TimelineState>((set) => ({
  ...seed,
  setCurrentTime: (currentTime) => set({ currentTime }),
  setPlaying: (isPlaying) => set({ isPlaying }),
  updateBlock: (track, id, patch) =>
    set((state) => ({
      [track]: state[track].map((block) => (block.id === id ? { ...block, ...patch } : block))
    }))
}));
