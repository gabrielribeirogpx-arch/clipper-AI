'use client';

import { ChangeEvent, DragEvent, MouseEvent, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { ApiError, createIngestStream, getIngestJobState, getIngestStatus, getUploadConfig, ingestYouTubeJob, uploadVideo } from '@/lib/api';
import { BROWSER_INTERNAL_SAVE_FOLDER_MESSAGE, INTERNAL_APP_FOLDER_LABEL, isAbsoluteLocalPath, isPlaceholderExportPath } from '@/lib/desktopBridge';
import { useUploadStore } from '@/store/uploadStore';
import { useTimelineStore } from '@/store/timelineStore';
import { useExportSettingsStore } from '@/store/exportSettingsStore';

const DEFAULT_UPLOAD_CONFIG = { max_upload_size_gb: 20, allowed_extensions: ['mp4', 'mov', 'mkv', 'webm'] };
const MAX_YOUTUBE_DURATION_SECONDS = 6 * 60 * 60;
const STALE_INGEST_MESSAGE = 'Previous ingest session expired. Please start a new analysis.';
const REAL_SAVE_FOLDER_MESSAGE = BROWSER_INTERNAL_SAVE_FOLDER_MESSAGE;

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

const formatTimestamp = (seconds: number) => {
  const total = Math.floor(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h}h${m}m${s}s`;
  return `${m}m${s}s`;
};

const toHhMmSs = (seconds: number) => {
  const total = Math.floor(seconds);
  const h = String(Math.floor(total / 3600)).padStart(2, '0');
  const m = String(Math.floor((total % 3600) / 60)).padStart(2, '0');
  const s = String(total % 60).padStart(2, '0');
  return `${h}:${m}:${s}`;
};

function YouTubeRangeSelector({
  duration,
  start,
  end,
  onStart,
  onEnd,
}: {
  duration: number;
  start: number;
  end: number;
  onStart: (value: number) => void;
  onEnd: (value: number) => void;
}) {
  const [isDragging, setDragging] = useState<'start' | 'end' | null>(null);
  const startPercent = (start / duration) * 100;
  const endPercent = (end / duration) * 100;

  return (
    <div className="space-y-3 rounded-2xl border border-white/10 bg-[#080f1f]/95 p-3">
      <div className="flex items-center justify-between text-xs uppercase tracking-[0.22em] text-slate-400">
        <span>Intervalo do vídeo fonte</span>
        <span>{formatTimestamp(end - start)} selecionados</span>
      </div>
      <div className="relative pt-4">
        <div className="pointer-events-none absolute inset-x-0 top-1/2 h-2 -translate-y-1/2 rounded-full bg-slate-800" />
        <div
          className="pointer-events-none absolute top-1/2 h-2 -translate-y-1/2 rounded-full bg-gradient-to-r from-cyan-400/90 to-violet-400/90 shadow-[0_0_24px_rgba(34,211,238,.45)] transition-all duration-150"
          style={{ left: `${startPercent}%`, width: `${endPercent - startPercent}%` }}
        />
        <input
          type="range"
          min={0}
          max={duration}
          value={start}
          onChange={(e) => onStart(clamp(Number(e.target.value), 0, end - 1))}
          onMouseDown={() => setDragging('start')}
          onMouseUp={() => setDragging(null)}
          onTouchStart={() => setDragging('start')}
          onTouchEnd={() => setDragging(null)}
          className="timeline-thumb pointer-events-auto absolute inset-0 w-full appearance-none bg-transparent"
        />
        <input
          type="range"
          min={0}
          max={duration}
          value={end}
          onChange={(e) => onEnd(clamp(Number(e.target.value), start + 1, duration))}
          onMouseDown={() => setDragging('end')}
          onMouseUp={() => setDragging(null)}
          onTouchStart={() => setDragging('end')}
          onTouchEnd={() => setDragging(null)}
          className="timeline-thumb pointer-events-auto absolute inset-0 w-full appearance-none bg-transparent"
        />
      </div>

      <div className="grid gap-2 text-sm text-slate-100 sm:grid-cols-2">
        <div className="rounded-xl border border-cyan-300/30 bg-cyan-300/5 p-2.5">
          <p className="text-xs uppercase tracking-[0.2em] text-cyan-200">Início da fonte</p>
          <p className="mt-0.5 text-base font-medium">{formatTimestamp(start)}</p>
          {isDragging === 'start' && <p className="text-xs text-cyan-300">Dragging preview</p>}
        </div>
        <div className="rounded-xl border border-violet-300/30 bg-violet-300/5 p-2.5">
          <p className="text-xs uppercase tracking-[0.2em] text-violet-200">Fim da fonte</p>
          <p className="mt-0.5 text-base font-medium">{formatTimestamp(end)}</p>
          {isDragging === 'end' && <p className="text-xs text-violet-300">Dragging preview</p>}
        </div>
      </div>

      {isDragging && (
        <div className="rounded-xl border border-white/10 bg-slate-900/90 p-3 text-xs text-slate-200">
          Thumbnail preview placeholder • {isDragging === 'start' ? formatTimestamp(start) : formatTimestamp(end)}
        </div>
      )}
    </div>
  );
}

const cleanDisplayError = (value: unknown): string => {
  const fallback = 'An error occurred. Please try again.';
  const raw = value instanceof Error ? value.message : String(value || fallback);
  try {
    const parsed = JSON.parse(raw) as { message?: unknown; detail?: unknown; error?: { message?: unknown } };
    const parsedMessage = parsed.message || parsed.error?.message || parsed.detail;
    if (typeof parsedMessage === 'string') return parsedMessage;
  } catch {
    // The error is already plain text.
  }
  return raw.length > 500 ? `${raw.slice(0, 500)}…` : raw;
};

export default function UploadPage() {
  const [isDragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [recentUploads, setRecentUploads] = useState<string[]>([]);
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [analysisName, setAnalysisName] = useState('');
  const [isStartingYoutubeIngest, setIsStartingYoutubeIngest] = useState(false);
  const renderMode = useUploadStore((state) => state.renderMode);
  const videoQuality = useUploadStore((state) => state.videoQuality);
  const [startSeconds, setStartSeconds] = useState(0);
  const [endSeconds, setEndSeconds] = useState(MAX_YOUTUBE_DURATION_SECONDS);
  const [minClipLength, setMinClipLength] = useState(30);
  const [maxClipLength, setMaxClipLength] = useState(90);
  const fileRef = useRef<File | null>(null);
  const ingestStreamRef = useRef<EventSource | null>(null);
  const activeStreamJobIdRef = useRef<string | null>(null);
  const ingestProgressListenerRef = useRef<((event: MessageEvent) => void) | null>(null);
  const reconnectTimersRef = useRef<Array<ReturnType<typeof setTimeout>>>([]);
  const dualRegionRedirectedRef = useRef(false);
  const router = useRouter();
  const store = useUploadStore();
  const resetForNewAnalysis = useTimelineStore((state) => state.resetForNewAnalysis);
  const hydrateFromBackend = useTimelineStore((state) => state.hydrateFromBackend);
  const semiAutoConfig = useTimelineStore((state) => state.semiAuto);
  const exportDirectory = useExportSettingsStore((state) => state.export_directory);
  const chooseExportFolder = useExportSettingsStore((state) => state.chooseExportFolder);
  const folderPickerUnsupported = useExportSettingsStore((state) => state.folderPickerUnsupported);
  const dismissFolderPickerUnsupported = useExportSettingsStore((state) => state.dismissFolderPickerUnsupported);
  const initializeExportSettings = useExportSettingsStore((state) => state.initialize);

  const resolveRedirectTarget = (analysisId: string, frontendRequestedMode: 'ai_tracking' | 'dual_region' | 'semi_auto' | 'raw_only', backendReturnedMode?: 'ai_tracking' | 'dual_region' | 'semi_auto' | 'raw_only') => {
    const hydratedMode = useTimelineStore.getState().clipRenderMode;
    console.log('[TIMELINE HYDRATED RENDER MODE]', { analysisId, clipRenderMode: hydratedMode });
    const resolvedMode = hydratedMode === 'semi_auto' || backendReturnedMode === 'semi_auto' || frontendRequestedMode === 'semi_auto'
      ? 'semi_auto'
      : (hydratedMode === 'dual_region' || backendReturnedMode === 'dual_region' || frontendRequestedMode === 'dual_region' ? 'dual_region' : 'ai_tracking');
    const target = resolvedMode === 'dual_region' ? `/region-setup/${analysisId}` : (resolvedMode === 'semi_auto' ? `/editor?analysis_id=${analysisId}` : `/editor?analysis_id=${analysisId}`);
    console.log('[DUAL REGION ROUTE CHECK]', {
      analysisId,
      frontendRequestedMode,
      backendReturnedMode: backendReturnedMode ?? null,
      hydratedMode,
      resolvedMode,
      routeTarget: target,
    });
    console.log('[REDIRECT TARGET]', { analysisId, target, resolvedMode });
    return target;
  };
  const redirectToPostAnalyzeTarget = (analysisId: string, frontendRequestedMode: 'ai_tracking' | 'dual_region' | 'semi_auto' | 'raw_only', backendReturnedMode?: 'ai_tracking' | 'dual_region' | 'semi_auto' | 'raw_only') => {
    if (dualRegionRedirectedRef.current) return;
    const uploadStatus = useUploadStore.getState().status;
    if (uploadStatus === 'waiting_dual_region') {
      useUploadStore.getState().updateIngestState({ analysisId, status: 'waiting_dual_region' });
      console.log('[DUAL REGION STATUS RECEIVED]', { analysis_id: analysisId, status: uploadStatus });
      console.log('[DUAL REGION REDIRECT]', analysisId);
      dualRegionRedirectedRef.current = true;
      router.push(`/region-setup/${analysisId}`);
      return;
    }
    if (uploadStatus === 'processing') {
      useUploadStore.getState().updateIngestState({ analysisId, status: 'processing' });
      console.log('[SEMI AUTO WAITING FOR SETUP]', { analysis_id: analysisId, status: uploadStatus });
      console.log('[SEMI AUTO REDIRECT]', analysisId);
      console.log('[SEMI AUTO SETUP REQUIRED]', { analysis_id: analysisId });
      dualRegionRedirectedRef.current = true;
      router.push(`/editor?analysis_id=${analysisId}`);
      return;
    }
    const target = resolveRedirectTarget(analysisId, frontendRequestedMode, backendReturnedMode);
    if (frontendRequestedMode === 'dual_region' || backendReturnedMode === 'dual_region') {
      const forcedTarget = `/region-setup/${analysisId}`;
      console.log('[DUAL REGION REDIRECT]', { frontendRequestedMode, backendReturnedMode: backendReturnedMode ?? null });
      console.log('[REDIRECT ANALYSIS ID]', analysisId);
      console.log('[REDIRECT TARGET FINAL]', forcedTarget);
      dualRegionRedirectedRef.current = true;
      router.push(forcedTarget);
      return;
    }
    if (frontendRequestedMode === 'semi_auto' || backendReturnedMode === 'semi_auto') {
      const forcedTarget = `/editor?analysis_id=${analysisId}`;
      console.log('[SEMI AUTO WAITING FOR SETUP]', { frontendRequestedMode, backendReturnedMode: backendReturnedMode ?? null });
      console.log('[SEMI AUTO REDIRECT]', analysisId);
      console.log('[SEMI AUTO SETUP REQUIRED]', { analysis_id: analysisId });
      dualRegionRedirectedRef.current = true;
      router.push(forcedTarget);
      return;
    }
    console.log('[REDIRECT ANALYSIS ID]', analysisId);
    console.log('[REDIRECT TARGET FINAL]', target);
    router.push(target);
  };

  const sizeLabel = useMemo(() => (store.uploadedVideo ? `${(store.uploadedVideo.size / (1024 * 1024)).toFixed(1)} MB` : null), [store.uploadedVideo]);
  const isUploadStatusInProgress = store.uploadStatus === 'uploading' || store.uploadStatus === 'processing';
  const isRealFileUploadActive = Boolean(store.uploadedVideo) && isUploadStatusInProgress;
  const isRealIngestActive = Boolean(store.activeJobId);
  const showUploadCard = isRealIngestActive || isStartingYoutubeIngest || isRealFileUploadActive;
  const uploadCardLabel = store.uploadStatus === 'uploading' ? 'Enviando vídeo grande, isso pode levar alguns minutos.' : (store.processingStage ?? store.currentStep ?? 'Processing...');
  const streamingStages = [
    ['Download', store.uploadProgress >= 10],
    ['Proxy / áudio / waveform', store.pipelineEvents.some((event) => event.stage === 'ingestion' && event.event === 'PIPELINE_STAGE_FINISHED')],
    ['Transcrição', store.pipelineEvents.some((event) => event.stage === 'transcription' && event.event === 'PIPELINE_STAGE_FINISHED')],
    ['Encontrando melhores momentos', store.pipelineEvents.some((event) => event.stage === 'fast_detection' && event.event === 'PIPELINE_STAGE_FINISHED')],
    ['Gerando primeiros clips', store.editorReady || store.clips.length > 0],
  ] as const;
  const hasRealExportDirectory = !isPlaceholderExportPath(exportDirectory) && isAbsoluteLocalPath(exportDirectory);
  const effectiveSaveFolder = hasRealExportDirectory ? exportDirectory : undefined;
  const [uploadConfig, setUploadConfig] = useState(DEFAULT_UPLOAD_CONFIG);
  const allowedFileExtensions = useMemo(() => uploadConfig.allowed_extensions.map((extension) => extension.startsWith('.') ? extension.toLowerCase() : `.${extension.toLowerCase()}`), [uploadConfig.allowed_extensions]);
  const uploadLimitBytes = uploadConfig.max_upload_size_gb > 0 ? uploadConfig.max_upload_size_gb * 1024 * 1024 * 1024 : 0;
  const uploadLimitLabel = `${uploadConfig.max_upload_size_gb}GB`;
  const validateFile = (file: File) => {
    const lowerName = file.name.toLowerCase();
    const hasAllowedExtension = allowedFileExtensions.some((extension) => lowerName.endsWith(extension));
    if (!hasAllowedExtension) return 'Formato inválido. Envie um arquivo MP4, MOV, MKV ou WEBM.';
    return uploadLimitBytes > 0 && file.size > uploadLimitBytes ? `Arquivo maior que o limite configurado de ${uploadLimitLabel}.` : null;
  };


  useEffect(() => {
    let cancelled = false;
    getUploadConfig()
      .then((config) => {
        if (!cancelled) setUploadConfig(config);
      })
      .catch((error) => console.warn('[UPLOAD CONFIG FALLBACK]', error));
    return () => { cancelled = true; };
  }, []);

  const selectLocalFile = (file: File) => {
    const validation = validateFile(file);
    if (validation) {
      setError(validation);
      return;
    }
    fileRef.current = file;
    setError(null);
    store.setUploadedVideo({ name: file.name, size: file.size, type: file.type || 'video/local', previewUrl: URL.createObjectURL(file) });
    store.setUploadStatus('idle');
    store.setProcessingStage('Upload pronto para iniciar.');
  };

  const processFile = async (file: File) => {
    dualRegionRedirectedRef.current = false;
    const validation = validateFile(file);
    if (validation) return setError(validation);
    if (!hasRealExportDirectory) setToast(REAL_SAVE_FOLDER_MESSAGE);
    setError(null);
    if (store.activeJobId) return setError('Já existe um job em execução. Aguarde finalizar.');
    resetForNewAnalysis();
    store.setUploadedVideo({ name: file.name, size: file.size, type: file.type, previewUrl: URL.createObjectURL(file) });
    store.setUploadStatus('uploading');
    store.setProcessingStage('Enviando vídeo grande, isso pode levar alguns minutos.');
    console.log('[UPLOAD SELECTED RENDER MODE]', { source: 'file_upload', renderMode });
    const result = await uploadVideo(file, analysisName, store.setUploadProgress, renderMode, videoQuality, effectiveSaveFolder, undefined, undefined, minClipLength, maxClipLength).catch((e) => {
      store.setUploadStatus('error');
      throw e;
    });
    store.setUploadStatus('processing');
    store.setUploadProgress(5);
    store.setProcessingStage('Upload concluído. Preparando análise');
    store.setActiveJob(result.job_id, result.analysis_id);
    console.log('[UPLOAD JOB CREATED]', { source: 'file_upload', job_id: result.job_id, analysis_id: result.analysis_id });
    const outcome = await subscribeToJob(result.job_id);
    if (outcome === 'completed') setRecentUploads((prev) => [file.name, ...prev].slice(0, 4));
  };

  const clearIngestResources = (jobId?: string) => {
    if (jobId && activeStreamJobIdRef.current && activeStreamJobIdRef.current !== jobId) return;

    reconnectTimersRef.current.forEach((timer) => clearTimeout(timer));
    reconnectTimersRef.current = [];

    if (ingestStreamRef.current) {
      if (ingestProgressListenerRef.current) {
        ingestStreamRef.current.removeEventListener('progress', ingestProgressListenerRef.current);
        ingestProgressListenerRef.current = null;
      }
      ingestStreamRef.current.close();
      ingestStreamRef.current = null;
      activeStreamJobIdRef.current = null;
    }

    console.log('[INGEST STREAM CLEANUP]');
  };

  const resetStaleIngest = (jobId: string, source: string) => {
    console.log('[STALE INGEST DETECTED]', { jobId, source });
    clearIngestResources(jobId);
    setIsStartingYoutubeIngest(false);

    const currentJobId = useUploadStore.getState().activeJobId;
    if (currentJobId && currentJobId !== jobId) return;

    useUploadStore.getState().resetStaleIngestVisualState();
    resetForNewAnalysis();
    fileRef.current = null;
    setDragging(false);
    setError(null);
    setYoutubeUrl('');
    setAnalysisName('');
    setStartSeconds(0);
    setEndSeconds(MAX_YOUTUBE_DURATION_SECONDS);
    setToast(STALE_INGEST_MESSAGE);
  };

  const isNotFoundError = (error: unknown) => error instanceof ApiError && error.status === 404;

  const finalizeJob = async (jobId: string) => {
    try {
      const result = await getIngestStatus(jobId);
      store.setUploadProgress(100);
      store.setUploadStatus('success');
      store.updateIngestState({ progress: 100, step: 'Completed', status: 'completed', clips: result.clips ?? [] });
      store.clearActiveJob();
      console.log('[FRONTEND JOB FINISHED]', { jobId });
      if ((result.clips?.length ?? 0) > 0) {
        console.log('[UPLOAD SUCCESS RENDER MODE]', { source: 'youtube_ingest', render_mode: renderMode, analysis_id: result.analysis_id });
        await hydrateFromBackend(result.analysis_id);
        setTimeout(() => {
          console.log('[FRONTEND ANALYSIS ID]', result.analysis_id);
          redirectToPostAnalyzeTarget(result.analysis_id, renderMode, result.render_mode);
        }, 600);
      }
      if (result.status === 'waiting_dual_region') {
        store.updateIngestState({ status: 'waiting_dual_region', analysisId: result.analysis_id });
        console.log('[DUAL REGION STATUS RECEIVED]', { analysis_id: result.analysis_id, status: result.status });
        setTimeout(() => redirectToPostAnalyzeTarget(result.analysis_id, renderMode, result.render_mode), 300);
      }
    } catch (error) {
      if (isNotFoundError(error)) {
        resetStaleIngest(jobId, 'status_404');
        return;
      }

      throw error;
    }
  };

  const subscribeToJob = (jobId: string) => new Promise<'completed' | 'stale'>((resolve, reject) => {
    const backoff = [1000, 2000, 5000, 10000];
    let retries = 0;
    let settled = false;

    const settle = (result: 'completed' | 'stale') => {
      if (settled) return;
      settled = true;
      resolve(result);
    };

    const cleanupAndSettleStale = (source: string) => {
      resetStaleIngest(jobId, source);
      settle('stale');
    };

    const verifyJobStillExists = async (source: string) => {
      try {
        await getIngestJobState(jobId);
        return true;
      } catch (error) {
        if (isNotFoundError(error)) {
          cleanupAndSettleStale(source);
          return false;
        }

        console.warn('[FRONTEND INGEST JOB VERIFY FAILED]', { jobId, source, error });
        return null;
      }
    };

    const connect = async () => {
      if (settled) return;

      const exists = await verifyJobStillExists('job_404_before_stream');
      if (exists === false || settled) return;

      if (ingestStreamRef.current) clearIngestResources();

      const stream = createIngestStream(jobId);
      ingestStreamRef.current = stream;
      activeStreamJobIdRef.current = jobId;

      const onProgress = (event: MessageEvent) => {
        const payload = JSON.parse(event.data) as { status: string; progress: number; step: string; clips?: Array<Record<string, unknown>>; analysis_id?: string; error?: { message?: string }; pipeline_event?: import('@/lib/api').PipelineEvent };
        store.setUploadProgress(payload.progress ?? 0);
        store.setProcessingStage(payload.step || 'Processing...');
        store.updateIngestState({
          progress: payload.progress ?? 0,
          step: payload.step || 'Processing...',
          status: payload.status,
          clips: payload.clips,
          analysisId: payload.analysis_id ?? useUploadStore.getState().analysisId,
          pipeline_event: payload.pipeline_event,
        });

        if (payload.status === 'waiting_dual_region') {
          const analysisId = payload.analysis_id ?? useUploadStore.getState().analysisId;
          console.log('[DUAL REGION STATUS RECEIVED]', payload);
          if (analysisId && !dualRegionRedirectedRef.current) {
            console.log('[DUAL REGION REDIRECT]', analysisId);
            dualRegionRedirectedRef.current = true;
            router.push(`/region-setup/${analysisId}`);
            return;
          }
        }
        if (payload.clips?.length && (payload.status === 'editor_ready' || payload.status === 'background_processing')) {
          const analysisId = payload.analysis_id ?? useUploadStore.getState().analysisId;
          if (analysisId && !dualRegionRedirectedRef.current) {
            void hydrateFromBackend(analysisId);
            console.log('[EDITOR READY REDIRECT]', analysisId);
            dualRegionRedirectedRef.current = true;
            router.push(`/editor?analysis_id=${analysisId}`);
          }
        }

        if (payload.status === 'completed') {
          stream.removeEventListener('progress', onProgress);
          stream.close();
          if (ingestStreamRef.current === stream) {
            ingestStreamRef.current = null;
            activeStreamJobIdRef.current = null;
            ingestProgressListenerRef.current = null;
          }
          void finalizeJob(jobId).then(() => settle('completed')).catch(reject);
        }

        if (payload.status === 'failed') {
          stream.removeEventListener('progress', onProgress);
          stream.close();
          if (ingestStreamRef.current === stream) {
            ingestStreamRef.current = null;
            activeStreamJobIdRef.current = null;
            ingestProgressListenerRef.current = null;
          }
          store.clearActiveJob();
          reject(new Error(payload.error?.message || 'YouTube ingest failed'));
        }
      };

      ingestProgressListenerRef.current = onProgress;
      stream.addEventListener('progress', onProgress);

      stream.onerror = () => {
        stream.removeEventListener('progress', onProgress);
        stream.close();
        if (ingestStreamRef.current === stream) {
          ingestStreamRef.current = null;
          activeStreamJobIdRef.current = null;
          ingestProgressListenerRef.current = null;
        }

        void verifyJobStillExists('stream_404').then((existsAfterError) => {
          if (existsAfterError === false || settled) return;

          const wait = backoff[Math.min(retries, backoff.length - 1)];
          retries += 1;
          console.log('[FRONTEND SSE RECONNECT]', { jobId, wait });
          const timer = setTimeout(() => {
            reconnectTimersRef.current = reconnectTimersRef.current.filter((item) => item !== timer);
            void connect().catch(reject);
          }, wait);
          reconnectTimersRef.current.push(timer);
        }).catch(reject);
      };
    };

    void connect().catch(reject);
  });

  const processYoutube = async () => {
    if (!youtubeUrl.trim()) return setError('Informe um link do YouTube ou selecione um arquivo de vídeo.');
    if (!hasRealExportDirectory) setToast(REAL_SAVE_FOLDER_MESSAGE);
    setError(null);
    if (store.activeJobId) return setError('Já existe um job em execução. Aguarde finalizar.');
    resetForNewAnalysis();
    dualRegionRedirectedRef.current = false;
    setIsStartingYoutubeIngest(true);
    store.setUploadStatus('processing');
    store.setProcessingStage('Starting YouTube ingest...');
    store.setUploadProgress(5);

    try {
      console.log('[UPLOAD SELECTED RENDER MODE]', { source: 'youtube_ingest', renderMode });

            const ingestPayload = {
        youtube_url: youtubeUrl.trim(),
        analysis_name: analysisName.trim() || undefined,
        source_start_time: toHhMmSs(startSeconds),
        source_end_time: toHhMmSs(endSeconds),
        min_clip_length: minClipLength,
        max_clip_length: maxClipLength,
        render_mode: renderMode,
                video_quality: videoQuality,
        ...(effectiveSaveFolder ? { save_folder: effectiveSaveFolder } : {}),
      };
      console.log('[FRONTEND INGEST PAYLOAD]', ingestPayload);
      const job = await ingestYouTubeJob(ingestPayload);

      store.setActiveJob(job.job_id, job.analysis_id);
      const result = await subscribeToJob(job.job_id);
      if (result === 'completed') setRecentUploads((prev) => [youtubeUrl, ...prev].slice(0, 4));
    } finally {
      setIsStartingYoutubeIngest(false);
    }
  };

  useEffect(() => {
    void initializeExportSettings();
  }, [initializeExportSettings]);

  useEffect(() => {
    console.log('[UPLOAD CARD ACTIVE STATE]', {
      showUploadCard,
      activeJobId: store.activeJobId,
      uploadStatus: store.uploadStatus,
      isStartingYoutubeIngest,
      hasUploadedVideo: Boolean(store.uploadedVideo),
      ingestStatus: store.status,
    });

    if (!showUploadCard) console.log('[UPLOAD CARD HIDDEN]');
  }, [showUploadCard, store.activeJobId, store.uploadStatus, isStartingYoutubeIngest, store.uploadedVideo, store.status]);

  useEffect(() => {
    const hasOrphanedInProgressState = !showUploadCard && !store.uploadedVideo && (isUploadStatusInProgress || store.uploadProgress > 0 || Boolean(store.processingStage) || Boolean(store.currentStep));
    if (!hasOrphanedInProgressState) return;

    store.resetUploadCardVisibilityState();
  }, [showUploadCard, store.uploadedVideo, isUploadStatusInProgress, store.uploadProgress, store.processingStage, store.currentStep, store]);

  useEffect(() => {
    if (!store.activeJobId) return () => clearIngestResources();
    console.log('[FRONTEND JOB RESTORE]', { jobId: store.activeJobId });
    void (async () => {
      const jobId = store.activeJobId as string;
      try {
        const state = await getIngestJobState(jobId);
        console.log('[FRONTEND JOB RESYNC]', state);
        store.setUploadStatus('processing');
        store.updateIngestState({ progress: state.progress, step: state.step, status: state.status, clips: state.clips, analysisId: state.analysis_id });
        if (state.status === 'waiting_dual_region') {
          console.log('[DUAL REGION STATUS RECEIVED]', state);
          if (state.analysis_id && !dualRegionRedirectedRef.current) {
            console.log('[DUAL REGION REDIRECT]', state.analysis_id);
            dualRegionRedirectedRef.current = true;
            router.push(`/region-setup/${state.analysis_id}`);
            return;
          }
        }
        if (state.status === 'processing') {
          console.log('[SEMI AUTO WAITING FOR SETUP]', state);
          if (state.analysis_id && !dualRegionRedirectedRef.current) {
            console.log('[SEMI AUTO REDIRECT]', state.analysis_id);
            console.log('[SEMI AUTO SETUP REQUIRED]', { analysis_id: state.analysis_id });
            dualRegionRedirectedRef.current = true;
            router.push(`/semi-auto/${state.analysis_id}`);
            return;
          }
        }
        if (state.status === 'completed') return finalizeJob(state.job_id);
        if (state.status !== 'failed') await subscribeToJob(state.job_id);
      } catch (error) {
        if (isNotFoundError(error)) {
          resetStaleIngest(jobId, 'job_404_restore');
          return;
        }

        throw error;
      }
    })().catch((e) => setError(cleanDisplayError(e)));
    return () => clearIngestResources();
  }, []);

  const handleAnalyze = (event: MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    console.log('[ANALYZE BUTTON CLICKED]');
    const selectedFile = fileRef.current;
    if (selectedFile) {
      void processFile(selectedFile).catch((e) => setError(cleanDisplayError(e)));
      return;
    }
    if (youtubeUrl.trim()) {
      void processYoutube().catch((e) => setError(cleanDisplayError(e)));
      return;
    }
    setError('Selecione um arquivo de vídeo ou informe um link do YouTube.');
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) selectLocalFile(file);
  };

  const onFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) selectLocalFile(file);
  };

  return (
    <main className="relative flex min-h-screen items-center overflow-hidden bg-[#050813] px-3 py-6 text-white sm:px-4 md:px-6">
      <style jsx>{`
        .timeline-thumb::-webkit-slider-thumb { appearance: none; height: 20px; width: 20px; border-radius: 9999px; background: linear-gradient(130deg, #67e8f9, #a78bfa); box-shadow: 0 0 18px rgba(103, 232, 249, 0.5); cursor: ew-resize; border: 2px solid #0b1220; }
        .timeline-thumb::-moz-range-thumb { height: 20px; width: 20px; border-radius: 9999px; background: linear-gradient(130deg, #67e8f9, #a78bfa); box-shadow: 0 0 18px rgba(103, 232, 249, 0.5); cursor: ew-resize; border: 2px solid #0b1220; }
      `}</style>
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(6,182,212,.25),transparent_36%),radial-gradient(circle_at_80%_15%,rgba(168,85,247,.22),transparent_36%)]" />
      <section className="upload-viewport-card timeline-scrollbar relative mx-auto w-full max-w-4xl rounded-[1.75rem] border border-white/15 bg-white/[0.04] p-4 shadow-[0_0_120px_rgba(34,211,238,.12)] backdrop-blur-3xl sm:p-5 md:p-6">
        <h1 className="text-center text-2xl font-semibold sm:text-3xl">Upload Cinematic AI</h1>
        <p className="mt-1.5 text-center text-sm text-slate-300 sm:text-base">Envie seu vídeo e gere uma timeline inteligente.</p>

        <motion.div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          animate={{ scale: isDragging ? 1.01 : 1, boxShadow: isDragging ? '0 0 50px rgba(34,211,238,.35)' : '0 0 20px rgba(168,85,247,.18)' }}
          className="mt-5 rounded-2xl border border-dashed border-cyan-300/45 bg-[#081025]/70 p-5 text-center sm:p-6"
        >
          <p className="text-base">Drag & drop MP4/MOV/MKV/WEBM</p>
          <label className="mx-auto mt-4 inline-flex cursor-pointer rounded-xl bg-gradient-to-r from-cyan-300 to-violet-500 px-5 py-2.5 text-sm font-semibold text-slate-950">
            Upload Video
            <input type="file" accept="video/mp4,video/quicktime,video/x-matroska,video/webm,.mp4,.mov,.mkv,.webm" className="hidden" onChange={onFileSelect} />
          </label>
        </motion.div>

        <div className="mt-5 grid gap-3 rounded-2xl border border-white/10 bg-white/[0.03] p-3 sm:p-4">
          <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
            <input value={analysisName} onChange={(e) => setAnalysisName(e.target.value)} placeholder="Nome da análise (opcional)" className="min-w-0 rounded-lg bg-slate-900 px-3 py-2 text-sm" />
            <div className="flex flex-wrap gap-2 text-sm text-slate-200 lg:justify-end">
            <button type="button" onClick={() => store.setRenderMode('ai_tracking')} className={`rounded-lg px-3 py-2 ${renderMode === 'ai_tracking' ? 'bg-cyan-400 text-black' : 'bg-slate-800'}`}>AI Tracking</button>
            <button type="button" onClick={() => store.setRenderMode('dual_region')} className={`rounded-lg px-3 py-2 ${renderMode === 'dual_region' ? 'bg-cyan-400 text-black' : 'bg-slate-800'}`}>Dual Region</button>
            <button type="button" onClick={() => { console.log('[SEMI AUTO MODE SELECTED]'); store.setRenderMode('semi_auto'); }} className={`rounded-lg px-3 py-2 ${renderMode === 'semi_auto' ? 'bg-cyan-400 text-black' : 'bg-slate-800'}`}>Semi Auto</button>
            </div>
          </div>

          <input value={youtubeUrl} onChange={(e) => setYoutubeUrl(e.target.value)} placeholder="https://youtube.com/live/..." className="rounded-lg bg-slate-900 px-3 py-2 text-sm" />
          <div className="rounded-xl border border-cyan-300/20 bg-slate-950/80 p-3 shadow-[0_0_30px_rgba(34,211,238,.08)] sm:flex sm:items-center sm:justify-between sm:gap-4">
            <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">📁 Save clips to:</p>
            <p className="mt-1 truncate text-sm text-cyan-200">{hasRealExportDirectory ? exportDirectory : INTERNAL_APP_FOLDER_LABEL}</p>
            <button type="button" onClick={() => void chooseExportFolder()} className="mt-3 shrink-0 rounded-lg border border-cyan-300/30 px-3 py-1.5 text-xs text-cyan-100 transition hover:bg-cyan-300/10 sm:mt-0">
              Change Folder
            </button>
          </div>
          {folderPickerUnsupported && (
            <div className="rounded-2xl border border-violet-300/30 bg-violet-500/10 px-4 py-3 text-sm text-violet-100" role="status">
              <p>{BROWSER_INTERNAL_SAVE_FOLDER_MESSAGE}</p>
              <button type="button" onClick={dismissFolderPickerUnsupported} className="mt-2 text-xs underline">
                Entendi
              </button>
            </div>
          )}
          <YouTubeRangeSelector duration={MAX_YOUTUBE_DURATION_SECONDS} start={startSeconds} end={endSeconds} onStart={setStartSeconds} onEnd={setEndSeconds} />
          <div className="grid gap-3 rounded-xl border border-white/10 bg-slate-950/70 p-3 text-sm text-slate-100 md:grid-cols-2">
            <label className="space-y-1">
              <span className="text-xs uppercase tracking-[0.18em] text-slate-400">Duração mínima de cada clipe (s)</span>
              <input type="number" min={10} max={maxClipLength} value={minClipLength} onChange={(e) => setMinClipLength(clamp(Number(e.target.value), 10, maxClipLength))} className="w-full rounded-lg bg-slate-900 px-3 py-2" />
            </label>
            <label className="space-y-1">
              <span className="text-xs uppercase tracking-[0.18em] text-slate-400">Duração máxima de cada clipe (s)</span>
              <input type="number" min={minClipLength} max={300} value={maxClipLength} onChange={(e) => setMaxClipLength(clamp(Number(e.target.value), minClipLength, 300))} className="w-full rounded-lg bg-slate-900 px-3 py-2" />
            </label>
          </div>
          <button type="button" onClick={handleAnalyze} className="rounded-xl bg-violet-500 px-4 py-2 text-sm font-semibold transition hover:bg-violet-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-300">
            Analisar vídeo
          </button>
        </div>

        {store.uploadedVideo && (
          <div className="mt-5 grid gap-4 rounded-2xl border border-white/10 bg-white/[0.03] p-4 md:grid-cols-2">
            <video src={store.uploadedVideo.previewUrl} className="h-52 w-full rounded-xl object-cover" controls />
            <div className="space-y-2 text-sm text-slate-200">
              <p>Arquivo: {store.uploadedVideo.name}</p>
              <p>Tamanho: {sizeLabel}</p>
              <p>Tipo: {store.uploadedVideo.type}</p>
              <p>Status: {store.uploadStatus}</p>
            </div>
          </div>
        )}

        {showUploadCard && (
          <div className="mt-5 space-y-3 rounded-2xl border border-cyan-300/25 bg-cyan-500/5 p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-cyan-100">{uploadCardLabel}</p>
                {(store.editorReady || store.backgroundProcessing) && (
                  <p className="mt-1 text-sm text-emerald-200">Você já pode editar enquanto continuamos processando.</p>
                )}
              </div>
              <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-200">{store.clips.length} clips</span>
            </div>
            <div className="h-2 rounded-full bg-slate-800">
              <div className="h-2 rounded-full bg-gradient-to-r from-cyan-300 to-violet-500" style={{ width: `${store.uploadProgress}%` }} />
            </div>
            <div className="grid gap-2 text-sm text-slate-200 sm:grid-cols-2">
              {streamingStages.map(([label, done]) => (
                <div key={label} className="flex items-center gap-2 rounded-xl border border-white/10 bg-black/15 px-3 py-2">
                  <span className={done ? 'text-emerald-300' : 'text-slate-500'}>{done ? '✔' : '•'}</span>
                  <span>{label}</span>
                </div>
              ))}
            </div>
            {store.backgroundProcessing && (
              <div className="grid gap-2 text-xs text-cyan-100 sm:grid-cols-2">
                <span className="rounded-xl bg-cyan-300/10 px-3 py-2">Gerando mais clips...</span>
                <span className="rounded-xl bg-violet-300/10 px-3 py-2">IA gerando títulos em background...</span>
              </div>
            )}
          </div>
        )}

        {toast && (
          <div className="mt-5 flex items-center justify-between gap-4 rounded-2xl border border-amber-300/30 bg-amber-300/10 px-4 py-3 text-sm text-amber-100" role="status">
            <span>{toast}</span>
            <button type="button" className="text-amber-50 underline" onClick={() => setToast(null)}>
              Dismiss
            </button>
          </div>
        )}

        {error && (
          <p className="mt-5 text-rose-300">
            {error}{' '}
            <button className="underline" onClick={() => fileRef.current && void processFile(fileRef.current).catch((e) => setError(cleanDisplayError(e)))}>
              Retry
            </button>
          </p>
        )}

        <div className="mt-5">
          <h3 className="text-sm uppercase tracking-[0.2em] text-slate-400">Recent uploads</h3>
          {recentUploads.map((name) => (
            <p key={name} className="mt-2 text-sm text-slate-300">
              • {name}
            </p>
          ))}
        </div>
      </section>
    </main>
  );
}
