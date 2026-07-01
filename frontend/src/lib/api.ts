export type UploadResponse = {
  success: boolean;
  status?: string;
  video_url: string;
  timeline: Record<string, unknown>;
  project_id: string;
  analysis_id?: string;
  render_mode?: RenderMode;
  duration: number;
  clips?: Array<Record<string, unknown>>;
};

export type RenderMode = "ai_tracking" | "dual_region" | "semi_auto" | "raw_only";

export type YouTubeIngestRequest = {
  youtube_url: string;
  analysis_name?: string;
  output_folder?: string;
  save_folder?: string;
  start_time?: string;
  end_time?: string;
  min_clip_length?: number;
  max_clip_length?: number;
  render_mode?: RenderMode;
  semi_auto_config?: Record<string, unknown>;
  video_quality?: '720p' | '1080p' | '4k';
};

export const API_BASE = (process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') || 'http://localhost:8000');

export const apiUrl = (path: string) => `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`;

const isAbsoluteLocalPath = (path: string) => /^(?:[a-zA-Z]:[\\/]|\\\\|\/)/.test(path);

const isInvalidSaveFolder = (path?: string | null) => {
  const value = (path ?? '').trim();
  if (!value) return true;
  return value.includes('<') || value.includes('>') || value.toLowerCase().includes('<user>') || !isAbsoluteLocalPath(value);
};

export const mediaUrl = (path?: string | null) => {
  if (!path) return null;
  if (/^https?:\/\//i.test(path)) return path;
  return apiUrl(path);
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    Object.setPrototypeOf(this, ApiError.prototype);
  }
}

async function responseErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const payload = await response.json() as { detail?: unknown; message?: unknown; error?: { message?: unknown } };
    const message = payload.error?.message || payload.message || payload.detail;
    return typeof message === 'string' ? message : fallback;
  } catch {
    return fallback;
  }
}


export function uploadVideo(
  file: File,
  analysisName?: string,
  onProgress?: (progress: number) => void,
  renderMode: RenderMode = "ai_tracking",
  videoQuality: '720p' | '1080p' | '4k' = '1080p',
  saveFolder?: string,
): Promise<UploadResponse> {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);
    if (analysisName?.trim()) formData.append('analysis_name', analysisName.trim());
    if (saveFolder?.trim() && !isInvalidSaveFolder(saveFolder)) formData.append('save_folder', saveFolder.trim());
    formData.append('render_mode', renderMode);
    formData.append('video_quality', videoQuality);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', apiUrl('/upload'));

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText) as UploadResponse);
      } else {
        void responseErrorMessage(new Response(xhr.responseText, { status: xhr.status }), 'Upload failed').then((message) => reject(new Error(message)));
      }
    };

    xhr.onerror = () => reject(new Error('Network error while uploading video'));
    xhr.send(formData);
  });
}

export async function getRenderState(analysisId?: string | null) {
  const query = analysisId ? `?analysis_id=${encodeURIComponent(analysisId)}` : '';
  const response = await fetch(apiUrl(`/timeline/render-state${query}`));
  if (!response.ok) throw new Error('Failed to fetch render state');
  return response.json();
}

export async function getTimeline() {
  const response = await fetch(apiUrl('/timeline'));
  if (!response.ok) throw new Error('Failed to fetch timeline');
  return response.json();
}

export async function ingestYouTubeVideo(payload: YouTubeIngestRequest): Promise<UploadResponse> {
  const response = await fetch(apiUrl('/ingest/youtube'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await responseErrorMessage(response, 'YouTube ingestion failed'));
  return response.json() as Promise<UploadResponse>;
}

export type ExportResponse = {
  success: boolean;
  export_path: string;
  download_url: string;
};

export async function exportClip(clipId: string): Promise<ExportResponse> {
  const response = await fetch(apiUrl('/export'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ clip_id: clipId }),
  });
  if (!response.ok) throw new Error('Export failed');
  return response.json() as Promise<ExportResponse>;
}


export type IngestJobResponse = { success: boolean; job_id: string; analysis_id: string; status: string };
export type PipelineEvent = { event: string; analysis_id: string; time: number; clip_count: number; total_time: number; stage?: string; message?: string };
export type IngestStatus = { status: string; progress: number; step: string; analysis_id: string; clips: Array<Record<string, unknown>>; error: unknown; render_mode?: RenderMode; pipeline_event?: PipelineEvent };
export type IngestJobState = IngestStatus & { job_id: string; finished: boolean };

export async function ingestYouTubeJob(payload: YouTubeIngestRequest): Promise<IngestJobResponse> {
  console.log('[FRONTEND SEMI AUTO SENT]', { semi_auto_config: payload.semi_auto_config, render_mode: payload.render_mode });
  const response = await fetch(apiUrl('/ingest/youtube'), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  if (!response.ok) throw new Error(await responseErrorMessage(response, 'YouTube ingestion failed'));
  return response.json() as Promise<IngestJobResponse>;
}

export async function getIngestStatus(jobId: string): Promise<IngestStatus> {
  const response = await fetch(apiUrl(`/ingest/status/${jobId}`));
  if (!response.ok) throw new ApiError("Failed to fetch ingest status", response.status);
  return response.json() as Promise<IngestStatus>;
}

export function createIngestStream(jobId: string): EventSource {
  return new EventSource(apiUrl(`/ingest/stream/${jobId}`));
}

export async function getIngestJobState(jobId: string): Promise<IngestJobState> {
  const response = await fetch(apiUrl(`/ingest/job/${jobId}`));
  if (!response.ok) throw new ApiError('Failed to fetch ingest job state', response.status);
  return response.json() as Promise<IngestJobState>;
}

export async function renderDualRegionFinal(payload: { analysis_id: string; render_mode: "dual_region"; dual_region_config: unknown }) {
  const response = await fetch(apiUrl('/timeline/render-dual-region'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error('Dual region render failed');
  return response.json();
}

export async function renderSemiAutoFinal(payload: { analysis_id: string; render_mode: "semi_auto"; semi_auto: unknown }) {
  const response = await fetch(apiUrl('/timeline/render-semi-auto'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error('Semi auto render failed');
  return response.json();
}
