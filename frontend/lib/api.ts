const API_BASE = process.env.NEXT_PUBLIC_API_URL
  ? `${process.env.NEXT_PUBLIC_API_URL}/api`
  : "/api";

const TOKEN_KEY = "bayyn_access_token";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

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
  progress_pct: number;
  current_step: string | null;
  retry_count: number;
  is_dead_letter: boolean;
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
  updated_at: string | null;
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

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string | null;
  name: string | null;
  is_active: boolean;
}

function authHeaders(): Record<string, string> {
  const token = getStoredToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...options?.headers,
    },
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
  // Auth
  register: (email: string, password: string, name?: string): Promise<TokenResponse> =>
    request("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, name }),
    }),

  login: (email: string, password: string): Promise<TokenResponse> =>
    request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  getMe: (): Promise<UserResponse> =>
    request("/auth/me"),

  // Transcription
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

  deleteJob: (jobId: string, options?: { hardDelete?: boolean }): Promise<void> => {
    const url = options?.hardDelete
      ? `/transcriptions/${jobId}?hard_delete=true`
      : `/transcriptions/${jobId}`;
    return request(url, { method: "DELETE" });
  },

  patchSegment: (jobId: string, sequenceNumber: number, text: string): Promise<TranscriptSegment> =>
    request(`/transcriptions/${jobId}/segments/${sequenceNumber}`, {
      method: "PATCH",
      body: JSON.stringify({ text }),
    }),

  exportUrl: (jobId: string, format: "txt" | "srt" | "docx", options?: { timestamps?: boolean }) => {
    const base = `${API_BASE}/transcriptions/${jobId}/export/${format}`;
    if (format === "txt" && options?.timestamps) return `${base}?timestamps=true`;
    return base;
  },
};
