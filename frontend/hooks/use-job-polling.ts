"use client";

import { useQuery } from "@tanstack/react-query";
import { api, TranscriptionJob } from "@/lib/api";

const TERMINAL_STATUSES = new Set(["completed", "failed", "cancelled"]);

export function useJobPolling(jobId: string) {
  return useQuery<TranscriptionJob>({
    queryKey: ["job", jobId],
    queryFn: () => api.getJob(jobId),
    refetchInterval: (query) => {
      const job = query.state.data;
      if (!job || TERMINAL_STATUSES.has(job.status)) {
        return false;
      }
      // Poll faster (1s) when actively progressing, slower (3s) when idle/queued
      const pct = job.progress_pct ?? 0;
      return pct > 0 && pct < 100 ? 1500 : 3000;
    },
    staleTime: 0,
  });
}

export function useTranscript(jobId: string, enabled: boolean) {
  return useQuery({
    queryKey: ["transcript", jobId],
    queryFn: () => api.getTranscript(jobId),
    enabled,
  });
}
