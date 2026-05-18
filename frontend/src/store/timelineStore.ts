'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { getRenderState } from '@/lib/api';

export type TrackType = 'broll' | 'hooks' | 'cuts' | 'effects';

export type BlockStyle = {
  color?: string;
  animation?: 'none' | 'fade' | 'pop' | 'smooth';
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
export type TimelineBlock = ClipBlock;

export type RenderJob = {
  id: string;
  clipName: string;
  state: 'queued' | 'rendering' | 'completed' | 'failed';
  progress: number;
};

export type GeneratedClip = {
  id: string;
  label: string;
  start: number;
  end: number;
  duration: number;
  clip_path: string;
  final_video: string;
  viral_score: number;
  hook_score: number;
  retention_score: number;
  emotion_score: number;
  title: string;
  caption: string;
  description: string;
  hashtags?: string[];
  raw_clip_path?: string;
};

type RenderMode = 'preview' | 'export';
export type ClipRenderMode = 'ai_tracking' | 'dual_region';
export type RegionBox = { x: number; y: number; width: number; height: number };
export type DualRegions = { regionA: RegionBox; regionB: RegionBox };

type TimelineState = {
  analysisId: string | null;
  renderMode: RenderMode;
  videoUrl: string | null;
  previewVideoUrl: string | null;
  exportVideoUrl: string | null;
  duration: number;
  currentTime: number;
  isPlaying: boolean;
  zoom: number;
  selectedBlockId: string | null;
  tracks: Record<TrackType, ClipBlock[]>;
  renderQueue: RenderJob[];
  generatedClips: GeneratedClip[];
  selectedClipId: string | null;
  clipRenderMode: ClipRenderMode;
  dualRegions: DualRegions;
  resetForNewAnalysis: () => void;
  hydrateFromBackend: () => Promise<void>;
  selectClip: (clipId: string) => void;
  setCurrentTime: (time: number) => void;
  setPlaying: (playing: boolean) => void;
  setZoom: (zoom: number) => void;
  selectBlock: (id: string | null) => void;
  updateBlock: (track: TrackType, id: string, patch: Partial<ClipBlock>) => void;
  moveBlock: (track: TrackType, id: string, start: number, end: number) => void;
  setClipRenderMode: (mode: ClipRenderMode) => void;
  setDualRegions: (regions: DualRegions) => void;
};

const clampTime = (value: number, duration: number) => Math.min(Math.max(value, 0), duration);
const SNAP = 0.1;
const snap = (time: number) => Math.round(time / SNAP) * SNAP;

const tracksSeed: Record<TrackType, ClipBlock[]> = {
  broll: [{ id: 'br-1', track: 'broll', label: 'B-roll Produto', start: 3, end: 8 }],
  hooks: [{ id: 'hk-1', track: 'hooks', label: 'Hook 1', start: 0, end: 2.5 }],
  cuts: [{ id: 'ct-1', track: 'cuts', label: 'Cut A', start: 8, end: 8.2 }],
  effects: [{ id: 'fx-1', track: 'effects', label: 'Glow', start: 1.4, end: 2.2 }]
};

export const useTimelineStore = create<TimelineState>()(persist((set, get) => ({
  analysisId: null,
  renderMode: 'preview',
  videoUrl: null,
  previewVideoUrl: null,
  exportVideoUrl: null,
  duration: 60,
  currentTime: 0,
  isPlaying: false,
  zoom: 1,
  selectedBlockId: null,
  tracks: { ...tracksSeed, effects: [] },
  renderQueue: [
    { id: 'job-1', clipName: 'Clip 01', state: 'queued', progress: 0 },
    { id: 'job-2', clipName: 'Clip 02', state: 'rendering', progress: 62 },
    { id: 'job-3', clipName: 'Clip 03', state: 'completed', progress: 100 },
    { id: 'job-4', clipName: 'Clip 04', state: 'failed', progress: 18 }
  ],
  generatedClips: [],
  selectedClipId: null,
  clipRenderMode: 'ai_tracking',
  dualRegions: {
    regionA: { x: 120, y: 80, width: 1680, height: 460 },
    regionB: { x: 120, y: 540, width: 1680, height: 460 },
  },
  resetForNewAnalysis: () =>
    set({
      analysisId: null,
      videoUrl: null,
      previewVideoUrl: null,
      exportVideoUrl: null,
      duration: 0,
      currentTime: 0,
      isPlaying: false,
      selectedBlockId: null,
      generatedClips: [],
      selectedClipId: null,
      tracks: {
        broll: [],
        hooks: [],
        cuts: [],
        effects: [],
      },
    }),
  setCurrentTime: (currentTime) => set({ currentTime: clampTime(currentTime, get().duration) }),
  setPlaying: (isPlaying) => set({ isPlaying }),
  setZoom: (zoom) => set({ zoom: Math.min(3, Math.max(0.5, zoom)) }),
  selectClip: (clipId) =>
    set((state) => {
      const clip = state.generatedClips.find((item) => item.id === clipId);
      if (!clip) return {};
      const nextVideoUrl = clip.final_video;
      return {
        selectedClipId: clipId,
        videoUrl: `http://localhost:8000${nextVideoUrl}`,
        duration: clip.duration,
        currentTime: clip.start,
      };
    }),
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
        broll: nextTracks.broll,
        hooks: nextTracks.hooks,
        cuts: nextTracks.cuts,
        render_mode: state.clipRenderMode,
        dual_regions: state.dualRegions,
      };
      void fetch('http://localhost:8000/timeline/update', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      return { tracks: nextTracks };
    }),
  setClipRenderMode: (clipRenderMode) =>
    set((state) => {
      void fetch('http://localhost:8000/timeline/update', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ broll: state.tracks.broll, hooks: state.tracks.hooks, cuts: state.tracks.cuts, render_mode: clipRenderMode, dual_regions: state.dualRegions }) });
      return { clipRenderMode };
    }),
  setDualRegions: (dualRegions) =>
    set((state) => {
      void fetch('http://localhost:8000/timeline/update', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ broll: state.tracks.broll, hooks: state.tracks.hooks, cuts: state.tracks.cuts, render_mode: state.clipRenderMode, dual_regions: dualRegions }) });
      return { dualRegions };
    }),
  hydrateFromBackend: async () => {
    const data = await getRenderState();
    const mapTrack = (items: ClipBlock[] = [], track: TrackType) =>
      items.map((item) => ({ ...item, track }));
    const previewVideoUrl = data.previewVideoUrl ? `http://localhost:8000${data.previewVideoUrl}` : null;
    const exportVideoUrl = data.exportVideoUrl ? `http://localhost:8000${data.exportVideoUrl}` : null;
    const renderMode: RenderMode = data.renderMode === 'export' ? 'export' : 'preview';
    const generatedClips: GeneratedClip[] = (data.clips ?? [])
      .map((clip: GeneratedClip) => ({ ...clip }))
      .sort((a: GeneratedClip, b: GeneratedClip) => b.viral_score - a.viral_score);
    const selectedClipId = generatedClips[0]?.id ?? null;
    const selectedClip = generatedClips[0];
    const backendAnalysisId: string | null = data.analysisId ?? null;
    const clipRenderMode: ClipRenderMode = data.render_mode === 'dual_region' ? 'dual_region' : 'ai_tracking';
    console.log('[RENDER MODE HYDRATED]', {
      analysisId: backendAnalysisId,
      render_mode: data.render_mode,
      clipRenderMode,
    });
    const currentAnalysisId = get().analysisId;
    const analysisChanged = currentAnalysisId !== backendAnalysisId;

    console.log('[BACKEND ANALYSIS_ID]', backendAnalysisId);
    console.log('[FRONTEND ACTIVE ANALYSIS_ID]', currentAnalysisId);
    if (analysisChanged) {
      console.log('[ANALYSIS CHANGED - CLEARING PREVIOUS STATE]', {
        from: currentAnalysisId,
        to: backendAnalysisId,
      });
    }
    console.log('[CURRENT CLIP SOURCE]', selectedClip?.final_video ?? data.previewVideoUrl ?? null);
    set({
      analysisId: backendAnalysisId,
      renderMode,
      previewVideoUrl,
      exportVideoUrl,
      videoUrl: selectedClip
        ? `http://localhost:8000${selectedClip.final_video}`
        : renderMode === 'export' ? exportVideoUrl : previewVideoUrl,
      duration: selectedClip?.duration ?? data.duration ?? 0,
      currentTime: selectedClip?.start ?? 0,
      isPlaying: false,
      selectedBlockId: null,
      generatedClips,
      selectedClipId,
      clipRenderMode,
      dualRegions: data.dual_regions ?? get().dualRegions,
      tracks: {
        broll: mapTrack(data.broll, 'broll'),
        hooks: mapTrack(data.hooks, 'hooks'),
        cuts: mapTrack(data.cuts, 'cuts'),
        effects: [],
      }
    });
    console.log('[FRONTEND ACTIVE ANALYSIS_ID]', backendAnalysisId);
  }
}), {
  name: 'clipper-timeline-state',
  partialize: (state) => ({
    analysisId: state.analysisId,
    renderMode: state.renderMode,
    videoUrl: state.videoUrl,
    previewVideoUrl: state.previewVideoUrl,
    exportVideoUrl: state.exportVideoUrl,
    duration: state.duration,
    currentTime: state.currentTime,
    zoom: state.zoom,
    tracks: state.tracks,
    renderQueue: state.renderQueue,
    generatedClips: state.generatedClips,
    selectedClipId: state.selectedClipId,
    clipRenderMode: state.clipRenderMode,
    dualRegions: state.dualRegions,
  }),
}));
