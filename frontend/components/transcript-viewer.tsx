"use client";

import { useState } from "react";
import { Copy, Check, Download, FileText, AlignLeft, Clock, AlertTriangle, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Transcript } from "@/lib/api";
import { formatTimestamp } from "@/lib/utils";

interface TranscriptViewerProps {
  transcript: Transcript;
  jobId: string;
  onDelete?: () => void;
  exportUrl: (format: "txt" | "srt" | "docx") => string;
}

export function TranscriptViewer({
  transcript,
  jobId,
  onDelete,
  exportUrl,
}: TranscriptViewerProps) {
  const [activeTab, setActiveTab] = useState<"full" | "segments">("full");
  const [copied, setCopied] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(transcript.full_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDelete = async () => {
    if (!onDelete) return;
    if (!confirm("Delete this transcript? This cannot be undone.")) return;
    setDeleting(true);
    onDelete();
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="completed">Transcript Ready</Badge>
          <span className="text-sm text-gray-500">
            {transcript.word_count.toLocaleString()} words ·{" "}
            {transcript.segment_count.toLocaleString()} segments
          </span>
          {transcript.average_confidence !== null && transcript.average_confidence !== undefined && (
            <span className="text-xs text-gray-400">
              avg. confidence{" "}
              <span
                className={
                  transcript.average_confidence >= 0.8
                    ? "text-green-600 font-medium"
                    : transcript.average_confidence >= 0.6
                    ? "text-yellow-600 font-medium"
                    : "text-red-500 font-medium"
                }
              >
                {(transcript.average_confidence * 100).toFixed(0)}%
              </span>
            </span>
          )}
          {transcript.has_low_confidence_segments && (
            <span className="inline-flex items-center gap-1 text-xs text-yellow-700 bg-yellow-50 border border-yellow-200 rounded px-2 py-0.5">
              <AlertTriangle className="w-3 h-3" />
              {transcript.low_confidence_count} low-confidence{" "}
              {transcript.low_confidence_count === 1 ? "segment" : "segments"}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Button variant="outline" size="sm" onClick={handleCopy}>
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 mr-1.5" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 mr-1.5" />
                Copy
              </>
            )}
          </Button>

          <a href={exportUrl("txt")} download>
            <Button variant="outline" size="sm">
              <Download className="w-3.5 h-3.5 mr-1.5" />
              TXT
            </Button>
          </a>
          <a href={exportUrl("srt")} download>
            <Button variant="outline" size="sm">
              <Download className="w-3.5 h-3.5 mr-1.5" />
              SRT
            </Button>
          </a>
          <a href={exportUrl("docx")} download>
            <Button variant="outline" size="sm">
              <FileText className="w-3.5 h-3.5 mr-1.5" />
              DOCX
            </Button>
          </a>

          {onDelete && (
            <Button
              variant="destructive"
              size="sm"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting ? "Deleting…" : "Delete Transcript"}
            </Button>
          )}
        </div>
      </div>

      {transcript.accuracy_disclaimer && (
        <div className="flex items-start gap-2 rounded-lg border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-800">
          <Info className="w-4 h-4 mt-0.5 shrink-0" />
          <span>{transcript.accuracy_disclaimer}</span>
        </div>
      )}

      <div className="flex border-b border-gray-100">
        <button
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "full"
              ? "border-bayyn-navy text-bayyn-navy"
              : "border-transparent text-gray-500 hover:text-bayyn-navy"
          }`}
          onClick={() => setActiveTab("full")}
        >
          <AlignLeft className="w-4 h-4" />
          Full Transcript
        </button>
        <button
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "segments"
              ? "border-bayyn-navy text-bayyn-navy"
              : "border-transparent text-gray-500 hover:text-bayyn-navy"
          }`}
          onClick={() => setActiveTab("segments")}
        >
          <Clock className="w-4 h-4" />
          Segments ({transcript.segment_count})
        </button>
      </div>

      {activeTab === "full" && (
        <div className="bg-white rounded-xl border border-gray-100 p-6 max-h-[60vh] overflow-y-auto">
          <p className="text-bayyn-text leading-relaxed whitespace-pre-wrap text-sm">
            {transcript.full_text}
          </p>
        </div>
      )}

      {activeTab === "segments" && (
        <div className="space-y-2 max-h-[60vh] overflow-y-auto">
          {transcript.segments.map((seg) => (
            <div
              key={seg.sequence_number}
              className={`flex gap-3 rounded-lg border p-3 transition-colors ${
                seg.low_confidence
                  ? "bg-yellow-50 border-yellow-200 hover:border-yellow-300"
                  : "bg-white border-gray-100 hover:border-bayyn-gold/30"
              }`}
            >
              <span className="shrink-0 font-mono text-xs text-bayyn-gold bg-bayyn-navy/5 rounded px-2 py-1 h-fit mt-0.5">
                {formatTimestamp(seg.start)}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-bayyn-text leading-relaxed">{seg.text}</p>
                {seg.low_confidence && (
                  <span className="inline-flex items-center gap-1 mt-1 text-xs text-yellow-700">
                    <AlertTriangle className="w-3 h-3" />
                    low confidence
                    {seg.confidence !== null && (
                      <span>({(seg.confidence * 100).toFixed(0)}%)</span>
                    )}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
