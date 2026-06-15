"use client";

import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  Loader2,
  AlertCircle,
  Clock,
  CheckCircle2,
  XCircle,
  ArrowLeft,
  Cpu,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TranscriptViewer } from "@/components/transcript-viewer";
import { useJobPolling, useTranscript } from "@/hooks/use-job-polling";
import { api } from "@/lib/api";
import { formatDate, formatDuration, STRATEGY_LABELS } from "@/lib/utils";
import { useQueryClient } from "@tanstack/react-query";

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="w-5 h-5 text-green-600" />;
    case "failed":
      return <XCircle className="w-5 h-5 text-red-600" />;
    case "processing":
      return <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />;
    default:
      return <Clock className="w-5 h-5 text-yellow-600" />;
  }
}

export default function JobPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const jobId = params.jobId as string;

  const { data: job, isLoading, error } = useJobPolling(jobId);
  const { data: transcript } = useTranscript(jobId, job?.status === "completed");

  const handleDelete = async () => {
    await api.deleteJob(jobId);
    router.push("/history");
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-bayyn-navy" />
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
        <h1 className="text-xl font-semibold text-bayyn-navy mb-2">Transcript Not Found</h1>
        <p className="text-gray-500 mb-6">
          This job ID doesn&apos;t exist or has been deleted.
        </p>
        <Link
          href="/"
          className="btn-primary inline-flex items-center gap-2 px-6 py-3 bg-bayyn-navy text-white rounded-lg font-semibold"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Home
        </Link>
      </div>
    );
  }

  const statusBadgeVariant = {
    pending: "pending",
    processing: "processing",
    completed: "completed",
    failed: "failed",
    cancelled: "cancelled",
  }[job.status] as any;

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <Link
        href="/"
        className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-bayyn-navy mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        New Transcript
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-bayyn-navy">
            {job.title || "Processing…"}
          </h1>
          {job.source_url && (
            <a
              href={job.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-gray-400 hover:text-bayyn-gold mt-1 block truncate max-w-md"
            >
              {job.source_url}
            </a>
          )}
        </div>
        <div className="flex items-center gap-2">
          <StatusIcon status={job.status} />
          <Badge variant={statusBadgeVariant} className="capitalize">
            {job.status}
          </Badge>
        </div>
      </div>

      <div className="grid sm:grid-cols-3 gap-4 mb-6">
        {job.duration_seconds !== null && (
          <div className="bg-white rounded-lg border border-gray-100 p-4">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Duration</p>
            <p className="font-semibold text-bayyn-navy">{formatDuration(job.duration_seconds)}</p>
          </div>
        )}
        {job.language && (
          <div className="bg-white rounded-lg border border-gray-100 p-4">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Language</p>
            <p className="font-semibold text-bayyn-navy uppercase">{job.language}</p>
          </div>
        )}
        <div className="bg-white rounded-lg border border-gray-100 p-4">
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Strategy</p>
          <div className="flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-bayyn-gold" />
            <p className="font-semibold text-bayyn-navy">
              {STRATEGY_LABELS[job.processing_strategy]}
            </p>
          </div>
        </div>
      </div>

      {(job.status === "pending" || job.status === "processing") && (
        <Card className="mb-6">
          <CardContent className="py-10 text-center">
            <Loader2 className="w-10 h-10 animate-spin text-bayyn-navy mx-auto mb-4" />
            <p className="text-bayyn-navy font-semibold mb-1">
              {job.status === "pending" ? "Queued for processing…" : "Extracting transcript…"}
            </p>
            <p className="text-sm text-gray-500 mb-4">
              {job.status === "pending"
                ? "Your job is in the queue."
                : job.current_step
                ? `Step: ${job.current_step.replace(/_/g, " ")}`
                : "Fetching captions or transcribing audio. This may take a moment."}
            </p>
            {job.progress_pct > 0 && (
              <div className="max-w-sm mx-auto">
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                  <span>Progress</span>
                  <span>{job.progress_pct}%</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
                  <div
                    className="h-2 rounded-full bg-bayyn-gold transition-all duration-700"
                    style={{ width: `${job.progress_pct}%` }}
                  />
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {job.status === "failed" && (
        <Card className="mb-6 border-red-200">
          <CardContent className="py-8 text-center">
            <XCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
            <p className="text-red-700 font-semibold mb-1">Transcription Failed</p>
            {job.error_message && (
              <p className="text-sm text-red-500">{job.error_message}</p>
            )}
            <Link
              href="/"
              className="mt-4 inline-flex items-center gap-2 text-sm text-bayyn-navy hover:underline"
            >
              Try a different URL →
            </Link>
          </CardContent>
        </Card>
      )}

      {job.status === "completed" && transcript && (
        <Card>
          <CardHeader>
            <CardTitle>Transcript</CardTitle>
          </CardHeader>
          <CardContent>
            <TranscriptViewer
              transcript={transcript}
              jobId={jobId}
              onDelete={handleDelete}
              exportUrl={(format) => api.exportUrl(jobId, format)}
            />
          </CardContent>
        </Card>
      )}

      <div className="mt-6 text-center text-xs text-gray-400">
        <span className="font-medium text-gray-500">Privacy: </span>
        No video or audio stored · Transcript only · Created{" "}
        {job.created_at ? formatDate(job.created_at) : ""}
      </div>
    </div>
  );
}
