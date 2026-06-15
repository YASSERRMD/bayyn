"use client";

import { useState } from "react";
import { Copy, Check, Download, FileText, AlignLeft, Clock } from "lucide-react";
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
        <div className="flex items-center gap-2">
          <Badge variant="completed">Transcript Ready</Badge>
          <span className="text-sm text-gray-500">
            {transcript.word_count.toLocaleString()} words ·{" "}
            {transcript.segment_count.toLocaleString()} segments
          </span>
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
              className="flex gap-3 bg-white rounded-lg border border-gray-100 p-3 hover:border-bayyn-gold/30 transition-colors"
            >
              <span className="shrink-0 font-mono text-xs text-bayyn-gold bg-bayyn-navy/5 rounded px-2 py-1 h-fit mt-0.5">
                {formatTimestamp(seg.start)}
              </span>
              <p className="text-sm text-bayyn-text leading-relaxed">{seg.text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
