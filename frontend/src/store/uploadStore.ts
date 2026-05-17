'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type UploadStatus = 'idle' | 'uploading' | 'processing' | 'success' | 'error';

type UploadedVideo = {
  name: string;
  size: number;
  type: string;
  duration?: number;
  previewUrl?: string;
};

type UploadState = {
  uploadProgress: number;
  uploadStatus: UploadStatus;
  processingStage: string;
  uploadedVideo: UploadedVideo | null;
  projectId: string | null;
  timelineData: Record<string, unknown> | null;
  activeJobId: string | null;
  analysisId: string | null;
  currentStep: string;
  status: string;
  clips: Array<Record<string, unknown>>;
  setUploadProgress: (progress: number) => void;
  setUploadStatus: (status: UploadStatus) => void;
  setProcessingStage: (stage: string) => void;
  setUploadedVideo: (video: UploadedVideo | null) => void;
  setUploadResult: (projectId: string, timelineData: Record<string, unknown>) => void;
  setActiveJob: (jobId: string, analysisId: string) => void;
  updateIngestState: (payload: { progress?: number; step?: string; status?: string; clips?: Array<Record<string, unknown>> }) => void;
  clearActiveJob: () => void;
  reset: () => void;
};

export const useUploadStore = create<UploadState>()(persist((set) => ({
  uploadProgress: 0,
  uploadStatus: 'idle',
  processingStage: 'Waiting for upload...',
  uploadedVideo: null,
  projectId: null,
  timelineData: null,
  activeJobId: null,
  analysisId: null,
  currentStep: 'Waiting for upload...',
  status: 'idle',
  clips: [],
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
  clearActiveJob: () => set({ activeJobId: null }),
  reset: () =>
    set({
      uploadProgress: 0,
      uploadStatus: 'idle',
      processingStage: 'Waiting for upload...',
      uploadedVideo: null,
      projectId: null,
      timelineData: null,
      activeJobId: null,
      analysisId: null,
      currentStep: 'Waiting for upload...',
      status: 'idle',
      clips: [],
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
}) }));
