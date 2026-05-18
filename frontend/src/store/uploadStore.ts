'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type UploadStatus = 'idle' | 'uploading' | 'processing' | 'success' | 'error';

const INITIAL_STATUS_LABEL = 'Waiting for upload...';

type UploadedVideo = {
  name: string;
  size: number;
  type: string;
  duration?: number;
  previewUrl?: string;
};

type RenderMode = 'ai_tracking' | 'dual_region';
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
  updateIngestState: (payload: { progress?: number; step?: string; status?: string; clips?: Array<Record<string, unknown>> }) => void;
  clearActiveJob: () => void;
  resetIngestState: () => void;
  resetStaleIngestVisualState: () => void;
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
  updateIngestState: ({ progress, step, status, clips }) => set((state) => ({
    uploadProgress: progress ?? state.uploadProgress,
    processingStage: step ?? state.processingStage,
    currentStep: step ?? state.currentStep,
    status: status ?? state.status,
    clips: clips ?? state.clips,
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
    });
  },
  resetStaleIngestVisualState: () => {
    console.log('[UPLOAD UI RESET]');
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
    });
    console.log('[UPLOAD VISUAL STATE CLEARED]');
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
}) }));
