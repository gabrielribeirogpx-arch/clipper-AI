'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type UploadStatus = 'idle' | 'uploading' | 'processing' | 'success' | 'error';

export type PipelineEvent = { event: string; analysis_id: string; time: number; clip_count: number; total_time: number; stage?: string; message?: string };

const INITIAL_STATUS_LABEL = 'Waiting for upload...';

type UploadedVideo = {
  name: string;
  size: number;
  type: string;
  duration?: number;
  previewUrl?: string;
};

type RenderMode = 'ai_tracking' | 'dual_region' | 'semi_auto' | 'raw_only';
type VideoQuality = '720p' | '1080p' | '4k';

type UploadState = {
  uploadProgress: number;
  uploadStatus: UploadStatus;
  processingStage: string | null;
  uploadedVideo: UploadedVideo | null;
  projectId: string | null;
  timelineData: Record<string, unknown> | null;
  activeJobId: string | null;
  analysisId: string | null;
  currentStep: string | null;
  status: string;
  clips: Array<Record<string, unknown>>;
  pipelineEvents: PipelineEvent[];
  editorReady: boolean;
  backgroundProcessing: boolean;
  renderMode: RenderMode;
  videoQuality: VideoQuality;
  setRenderMode: (mode: RenderMode) => void;
  setVideoQuality: (quality: VideoQuality) => void;
  setUploadProgress: (progress: number) => void;
  setUploadStatus: (status: UploadStatus) => void;
  setProcessingStage: (stage: string | null) => void;
  setUploadedVideo: (video: UploadedVideo | null) => void;
  setUploadResult: (projectId: string, timelineData: Record<string, unknown>) => void;
  setActiveJob: (jobId: string, analysisId: string) => void;
  updateIngestState: (payload: { progress?: number; step?: string; status?: string; clips?: Array<Record<string, unknown>>; analysisId?: string | null; pipeline_event?: PipelineEvent }) => void;
  clearActiveJob: () => void;
  resetIngestState: () => void;
  resetStaleIngestVisualState: () => void;
  resetUploadCardVisibilityState: () => void;
  reset: () => void;
};

export const useUploadStore = create<UploadState>()(persist((set) => ({
  uploadProgress: 0,
  uploadStatus: 'idle',
  processingStage: INITIAL_STATUS_LABEL,
  uploadedVideo: null,
  projectId: null,
  timelineData: null,
  activeJobId: null,
  analysisId: null,
  currentStep: INITIAL_STATUS_LABEL,
  status: 'idle',
  clips: [],
  pipelineEvents: [],
  editorReady: false,
  backgroundProcessing: false,
  renderMode: 'ai_tracking',
  videoQuality: '1080p',
  setUploadProgress: (uploadProgress) => set({ uploadProgress }),
  setUploadStatus: (uploadStatus) => set({ uploadStatus }),
  setProcessingStage: (processingStage) => set({ processingStage }),
  setUploadedVideo: (uploadedVideo) => set({ uploadedVideo }),
  setUploadResult: (projectId, timelineData) => set({ projectId, timelineData }),
  setActiveJob: (activeJobId, analysisId) => {
    console.log('[FRONTEND ACTIVE JOB]', { activeJobId, analysisId });
    set({ activeJobId, analysisId, status: 'processing' });
  },
  updateIngestState: ({ progress, step, status, clips, analysisId, pipeline_event }) => set((state) => ({
    uploadProgress: progress ?? state.uploadProgress,
    processingStage: step ?? state.processingStage,
    currentStep: step ?? state.currentStep,
    status: status ?? state.status,
    clips: clips ?? state.clips,
    analysisId: analysisId ?? state.analysisId,
    pipelineEvents: pipeline_event ? [...state.pipelineEvents, pipeline_event].slice(-80) : state.pipelineEvents,
    editorReady: state.editorReady || pipeline_event?.event === 'EDITOR_READY' || status === 'editor_ready' || status === 'background_processing',
    backgroundProcessing: pipeline_event?.event === 'BACKGROUND_PROCESSING' || status === 'background_processing' ? true : (status === 'completed' ? false : state.backgroundProcessing),
  })),
  setRenderMode: (renderMode) => {
    console.log('[RENDER MODE SAVED]', { renderMode });
    set({ renderMode });
  },
  setVideoQuality: (videoQuality) => {
    console.log('[DOWNLOAD QUALITY SELECTED]', { videoQuality });
    set({ videoQuality });
  },
  clearActiveJob: () => set({ activeJobId: null }),
  resetIngestState: () => {
    console.log('[INGEST STATE RESET]');
    set({
      uploadProgress: 0,
      uploadStatus: 'idle',
      processingStage: INITIAL_STATUS_LABEL,
      activeJobId: null,
      analysisId: null,
      currentStep: INITIAL_STATUS_LABEL,
      status: 'idle',
      clips: [],
      pipelineEvents: [],
      editorReady: false,
      backgroundProcessing: false,
    });
  },
  resetStaleIngestVisualState: () => {
    console.log('[UPLOAD UI RESET]');
    console.log('[UPLOAD CARD VISIBILITY RESET]');
    set({
      uploadProgress: 0,
      uploadStatus: 'idle',
      processingStage: null,
      uploadedVideo: null,
      projectId: null,
      timelineData: null,
      activeJobId: null,
      analysisId: null,
      currentStep: null,
      status: 'idle',
      clips: [],
      pipelineEvents: [],
      editorReady: false,
      backgroundProcessing: false,
    });
    console.log('[UPLOAD VISUAL STATE CLEARED]');
  },

  resetUploadCardVisibilityState: () => {
    console.log('[UPLOAD CARD VISIBILITY RESET]');
    set({
      uploadProgress: 0,
      uploadStatus: 'idle',
      processingStage: null,
      currentStep: null,
      status: 'idle',
      activeJobId: null,
      analysisId: null,
    });
  },
  reset: () =>
    set({
      uploadProgress: 0,
      uploadStatus: 'idle',
      processingStage: INITIAL_STATUS_LABEL,
      uploadedVideo: null,
      projectId: null,
      timelineData: null,
      activeJobId: null,
      analysisId: null,
      currentStep: INITIAL_STATUS_LABEL,
      status: 'idle',
      clips: [],
      pipelineEvents: [],
      editorReady: false,
      backgroundProcessing: false,
      renderMode: 'ai_tracking',
      videoQuality: '1080p',
    }),
}), { name: 'clipper-upload-state', partialize: (state) => ({
  uploadProgress: state.uploadProgress,
  uploadStatus: state.uploadStatus,
  processingStage: state.processingStage,
  projectId: state.projectId,
  timelineData: state.timelineData,
  activeJobId: state.activeJobId,
  analysisId: state.analysisId,
  currentStep: state.currentStep,
  status: state.status,
  clips: state.clips,
  renderMode: state.renderMode,
  videoQuality: state.videoQuality,
  pipelineEvents: state.pipelineEvents,
  editorReady: state.editorReady,
  backgroundProcessing: state.backgroundProcessing,
}) }));
