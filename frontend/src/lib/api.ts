export type UploadResponse = {
  success: boolean;
  video_url: string;
  timeline: Record<string, unknown>;
  project_id: string;
  duration: number;
  clips?: Array<Record<string, unknown>>;
};

export type YouTubeIngestRequest = {
  youtube_url: string;
  start_time?: string;
  end_time?: string;
  min_clip_length?: number;
  max_clip_length?: number;
};

const API_BASE = 'http://localhost:8000';

export function uploadVideo(
  file: File,
  onProgress?: (progress: number) => void,
): Promise<UploadResponse> {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);

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

export async function getRenderState() {
  const response = await fetch(`${API_BASE}/timeline/render-state`);
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
