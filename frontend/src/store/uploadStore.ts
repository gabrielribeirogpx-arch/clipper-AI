'use client';

import { create } from 'zustand';

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
  setUploadProgress: (progress: number) => void;
  setUploadStatus: (status: UploadStatus) => void;
  setProcessingStage: (stage: string) => void;
  setUploadedVideo: (video: UploadedVideo | null) => void;
  setUploadResult: (projectId: string, timelineData: Record<string, unknown>) => void;
  reset: () => void;
};

export const useUploadStore = create<UploadState>((set) => ({
  uploadProgress: 0,
  uploadStatus: 'idle',
  processingStage: 'Waiting for upload...',
  uploadedVideo: null,
  projectId: null,
  timelineData: null,
  setUploadProgress: (uploadProgress) => set({ uploadProgress }),
  setUploadStatus: (uploadStatus) => set({ uploadStatus }),
  setProcessingStage: (processingStage) => set({ processingStage }),
  setUploadedVideo: (uploadedVideo) => set({ uploadedVideo }),
  setUploadResult: (projectId, timelineData) => set({ projectId, timelineData }),
  reset: () =>
    set({
      uploadProgress: 0,
      uploadStatus: 'idle',
      processingStage: 'Waiting for upload...',
      uploadedVideo: null,
      projectId: null,
      timelineData: null,
    }),
}));
