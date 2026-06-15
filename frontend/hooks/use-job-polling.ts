"use client";

import { useQuery } from "@tanstack/react-query";
import { api, TranscriptionJob } from "@/lib/api";

export function useJobPolling(jobId: string) {
  return useQuery<TranscriptionJob>({
    queryKey: ["job", jobId],
    queryFn: () => api.getJob(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed" || status === "cancelled") {
        return false;
      }
      return 2000;
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
