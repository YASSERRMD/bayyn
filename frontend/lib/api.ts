const API_BASE = process.env.NEXT_PUBLIC_API_URL
  ? `${process.env.NEXT_PUBLIC_API_URL}/api`
  : "/api";

export type JobStatus = "pending" | "processing" | "completed" | "failed" | "cancelled";
export type ProcessingStrategy = "caption" | "whisper" | "unknown";

export interface TranscriptionJob {
  job_id: string;
  source_url: string;
  source_type: string;
  source_domain: string | null;
  title: string | null;
  duration_seconds: number | null;
  language: string | null;
  status: JobStatus;
  processing_strategy: ProcessingStrategy;
  error_message: string | null;
  media_stored: boolean;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface TranscriptSegment {
  sequence_number: number;
  start: number;
  end: number;
  text: string;
  confidence: number | null;
  speaker_label: string | null;
  low_confidence: boolean;
}

export interface Transcript {
  job_id: string;
  full_text: string;
  word_count: number;
  segment_count: number;
  average_confidence: number | null;
  low_confidence_count: number;
  has_low_confidence_segments: boolean;
  accuracy_disclaimer: string | null;
  segments: TranscriptSegment[];
  created_at: string;
}

export interface CreateJobResponse {
  job_id: string;
  status: JobStatus;
}

export interface JobListResponse {
  jobs: TranscriptionJob[];
  total: number;
}

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });

  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      errorDetail = body.detail || body.message || errorDetail;
    } catch {}
    throw new Error(errorDetail);
  }

  if (res.status === 204) return undefined as unknown as T;
  return res.json();
}

export const api = {
  createJob: (url: string): Promise<CreateJobResponse> =>
    request("/transcriptions", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),

  listJobs: (offset = 0, limit = 50): Promise<JobListResponse> =>
    request(`/transcriptions?offset=${offset}&limit=${limit}`),

  getJob: (jobId: string): Promise<TranscriptionJob> =>
    request(`/transcriptions/${jobId}`),

  getTranscript: (jobId: string): Promise<Transcript> =>
    request(`/transcriptions/${jobId}/transcript`),

  deleteJob: (jobId: string): Promise<void> =>
    request(`/transcriptions/${jobId}`, { method: "DELETE" }),

  exportUrl: (jobId: string, format: "txt" | "srt" | "docx") =>
    `${API_BASE}/transcriptions/${jobId}/export/${format}`,
};
