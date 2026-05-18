export type UploadResponse = {
  success: boolean;
  video_url: string;
  timeline: Record<string, unknown>;
  project_id: string;
  analysis_id?: string;
  duration: number;
  clips?: Array<Record<string, unknown>>;
};

export type RenderMode = "ai_tracking" | "dual_region";

export type YouTubeIngestRequest = {
  youtube_url: string;
  analysis_name?: string;
  output_folder?: string;
  start_time?: string;
  end_time?: string;
  min_clip_length?: number;
  max_clip_length?: number;
  render_mode?: RenderMode;
  video_quality?: '720p' | '1080p' | '4k';
};

const API_BASE = 'http://localhost:8000';

export function uploadVideo(
  file: File,
  analysisName?: string,
  onProgress?: (progress: number) => void,
  renderMode: RenderMode = "ai_tracking",
  videoQuality: '720p' | '1080p' | '4k' = '1080p',
): Promise<UploadResponse> {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);
    if (analysisName?.trim()) formData.append('analysis_name', analysisName.trim());
    formData.append('render_mode', renderMode);
    formData.append('video_quality', videoQuality);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE}/upload`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText) as UploadResponse);
      } else {
        reject(new Error('Upload failed'));
      }
    };

    xhr.onerror = () => reject(new Error('Network error while uploading video'));
    xhr.send(formData);
  });
}

export async function getRenderState(analysisId?: string | null) {
  const query = analysisId ? `?analysis_id=${encodeURIComponent(analysisId)}` : '';
  const response = await fetch(`${API_BASE}/timeline/render-state${query}`);
  if (!response.ok) throw new Error('Failed to fetch render state');
  return response.json();
}

export async function getTimeline() {
  const response = await fetch(`${API_BASE}/timeline`);
  if (!response.ok) throw new Error('Failed to fetch timeline');
  return response.json();
}

export async function ingestYouTubeVideo(payload: YouTubeIngestRequest): Promise<UploadResponse> {
  const response = await fetch(`${API_BASE}/ingest/youtube`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error('YouTube ingestion failed');
  return response.json() as Promise<UploadResponse>;
}

export type ExportResponse = {
  success: boolean;
  export_path: string;
  download_url: string;
};

export async function exportClip(clipId: string): Promise<ExportResponse> {
  const response = await fetch(`${API_BASE}/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ clip_id: clipId }),
  });
  if (!response.ok) throw new Error('Export failed');
  return response.json() as Promise<ExportResponse>;
}


export type IngestJobResponse = { success: boolean; job_id: string; analysis_id: string; status: string };
export type IngestStatus = { status: string; progress: number; step: string; analysis_id: string; clips: Array<Record<string, unknown>>; error: unknown };
export type IngestJobState = IngestStatus & { job_id: string; finished: boolean };

export async function ingestYouTubeJob(payload: YouTubeIngestRequest): Promise<IngestJobResponse> {
  const response = await fetch(`${API_BASE}/ingest/youtube`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  if (!response.ok) throw new Error("YouTube ingestion failed");
  return response.json() as Promise<IngestJobResponse>;
}

export async function getIngestStatus(jobId: string): Promise<IngestStatus> {
  const response = await fetch(`${API_BASE}/ingest/status/${jobId}`);
  if (!response.ok) throw new Error("Failed to fetch ingest status");
  return response.json() as Promise<IngestStatus>;
}

export function createIngestStream(jobId: string): EventSource {
  return new EventSource(`${API_BASE}/ingest/stream/${jobId}`);
}

export async function getIngestJobState(jobId: string): Promise<IngestJobState> {
  const response = await fetch(`${API_BASE}/ingest/job/${jobId}`);
  if (!response.ok) throw new Error('Failed to fetch ingest job state');
  return response.json() as Promise<IngestJobState>;
}

export async function renderDualRegionFinal(payload: { analysis_id: string; render_mode: "dual_region"; dual_region_config: unknown }) {
  const response = await fetch(`${API_BASE}/timeline/render-dual-region`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error('Dual region render failed');
  return response.json();
}
