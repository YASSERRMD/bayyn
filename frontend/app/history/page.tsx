"use client";

import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2, AlertCircle, Trash2, ExternalLink, FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, TranscriptionJob } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatDate, formatDuration, STATUS_LABELS } from "@/lib/utils";

export default function HistoryPage() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
    }
  }, [authLoading, user, router]);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => api.listJobs(),
    enabled: !!user,
  });

  if (authLoading || (!user && !authLoading)) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-bayyn-navy" />
      </div>
    );
  }

  const handleDelete = async (jobId: string) => {
    if (!confirm("Delete this transcript? This cannot be undone.")) return;
    await api.deleteJob(jobId);
    queryClient.invalidateQueries({ queryKey: ["jobs"] });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-bayyn-navy" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-4" />
        <p className="text-gray-600">Failed to load history. Please try again.</p>
        <Button className="mt-4" onClick={() => refetch()}>
          Retry
        </Button>
      </div>
    );
  }

  const jobs = data?.jobs ?? [];

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-bayyn-navy">Transcript History</h1>
          <p className="text-gray-500 mt-1">
            {data?.total ?? 0} transcript{data?.total !== 1 ? "s" : ""} stored
          </p>
        </div>
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-bayyn-navy text-white rounded-lg text-sm font-semibold hover:bg-opacity-90 transition-all"
        >
          <FileText className="w-4 h-4" />
          New Transcript
        </Link>
      </div>

      {jobs.length === 0 ? (
        <div className="text-center py-20">
          <div className="text-6xl mb-4">📄</div>
          <h2 className="text-xl font-semibold text-bayyn-navy mb-2">No transcripts yet</h2>
          <p className="text-gray-500 mb-6">
            Paste a YouTube URL to create your first transcript.
          </p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-6 py-3 bg-bayyn-navy text-white rounded-lg font-semibold hover:bg-opacity-90 transition-all"
          >
            Get Started
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {jobs.map((job: TranscriptionJob) => (
            <div
              key={job.job_id}
              className="bg-white rounded-xl border border-gray-100 p-5 hover:border-bayyn-gold/30 transition-all hover:shadow-sm"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <Link
                    href={`/transcriptions/${job.job_id}`}
                    className="font-semibold text-bayyn-navy hover:text-bayyn-gold transition-colors truncate block"
                  >
                    {job.title || job.source_url}
                  </Link>
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1.5">
                    <span className="text-xs text-gray-400 capitalize">{job.source_type}</span>
                    {job.duration_seconds !== null && (
                      <span className="text-xs text-gray-400">
                        {formatDuration(job.duration_seconds)}
                      </span>
                    )}
                    <span className="text-xs text-gray-400">{formatDate(job.created_at)}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Badge
                    variant={job.status as any}
                    className="capitalize"
                  >
                    {STATUS_LABELS[job.status]}
                  </Badge>
                  <Link href={`/transcriptions/${job.job_id}`}>
                    <Button variant="ghost" size="icon">
                      <ExternalLink className="w-4 h-4" />
                    </Button>
                  </Link>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDelete(job.job_id)}
                    className="text-red-400 hover:text-red-600 hover:bg-red-50"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
