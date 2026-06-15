import { Shield, Database, Trash2, Clock, Lock } from "lucide-react";

function PolicySection({
  icon: Icon,
  title,
  children,
}: {
  icon: React.ElementType;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex gap-5 p-6 bg-white rounded-xl border border-gray-100">
      <div className="shrink-0 w-10 h-10 rounded-full bg-bayyn-navy/10 flex items-center justify-center">
        <Icon className="w-5 h-5 text-bayyn-navy" />
      </div>
      <div>
        <h3 className="font-semibold text-bayyn-navy mb-2">{title}</h3>
        <div className="text-sm text-gray-600 leading-relaxed space-y-1">{children}</div>
      </div>
    </div>
  );
}

function StorageTable({
  title,
  items,
  stored,
}: {
  title: string;
  items: string[];
  stored: boolean;
}) {
  return (
    <div>
      <h3 className="font-semibold text-bayyn-navy mb-3">{title}</h3>
      <ul className="space-y-2">
        {items.map((item) => (
          <li key={item} className="flex items-center gap-3 text-sm">
            <span
              className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${
                stored ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"
              }`}
            >
              {stored ? "✓" : "✕"}
            </span>
            <span className={stored ? "text-gray-700" : "text-gray-500"}>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function PrivacyPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <div className="text-center mb-12">
        <div className="w-16 h-16 bg-bayyn-navy rounded-2xl flex items-center justify-center mx-auto mb-4">
          <Shield className="w-8 h-8 text-bayyn-gold" />
        </div>
        <h1 className="text-4xl font-bold text-bayyn-navy mb-3">Privacy Policy</h1>
        <p className="text-gray-500 text-lg max-w-xl mx-auto">
          Bayyn is built on one principle: store knowledge, not media. Here&apos;s exactly what
          that means.
        </p>
      </div>

      <div className="space-y-4 mb-10">
        <PolicySection icon={Database} title="What Bayyn Stores">
          <p>Only the transcript and its metadata are permanently stored:</p>
          <ul className="mt-2 space-y-1 list-disc list-inside">
            <li>Transcript full text</li>
            <li>Timestamped transcript segments</li>
            <li>Source URL (for attribution)</li>
            <li>Video title and duration</li>
            <li>Language and processing method</li>
            <li>Job status and dates</li>
          </ul>
        </PolicySection>

        <PolicySection icon={Lock} title="What Bayyn Never Stores">
          <p>The following are never written to permanent storage — not even temporarily in a way that persists:</p>
          <ul className="mt-2 space-y-1 list-disc list-inside">
            <li>Video files</li>
            <li>Audio files</li>
            <li>Thumbnails</li>
            <li>Raw downloaded media of any kind</li>
            <li>Temporary file paths (only a hash is logged)</li>
            <li>Raw audio stream URLs</li>
          </ul>
        </PolicySection>

        <PolicySection icon={Clock} title="Temporary Processing Only">
          <p>
            When captions are not available, Bayyn uses ffmpeg and faster-whisper to transcribe
            audio. During this process:
          </p>
          <ul className="mt-2 space-y-1 list-disc list-inside">
            <li>Audio is processed in an isolated temporary directory</li>
            <li>The temporary directory is deleted immediately after transcription</li>
            <li>The directory is deleted whether the job succeeds or fails</li>
            <li>Stale directories older than 1 hour are cleaned up on startup</li>
            <li>No Docker volume for media storage exists</li>
          </ul>
        </PolicySection>

        <PolicySection icon={Trash2} title="Your Right to Delete">
          <p>
            You can delete any transcript at any time from the job page or transcript history. When
            you delete a transcript:
          </p>
          <ul className="mt-2 space-y-1 list-disc list-inside">
            <li>The full transcript text is deleted</li>
            <li>All timestamped segments are deleted</li>
            <li>The job record is soft-deleted (source URL retained for audit only)</li>
            <li>No media to delete — it was never stored</li>
          </ul>
        </PolicySection>
      </div>

      <div className="grid sm:grid-cols-2 gap-6 mb-10">
        <StorageTable
          title="Stored in Database"
          stored={true}
          items={[
            "Transcript text",
            "Segment timestamps",
            "Source URL",
            "Video title",
            "Duration",
            "Language",
            "Processing method",
          ]}
        />
        <StorageTable
          title="Never Stored"
          stored={false}
          items={[
            "Video files (.mp4, .webm)",
            "Audio files (.mp3, .wav, .m4a)",
            "Thumbnails",
            "Downloaded media",
            "Temp file paths",
            "Audio stream URLs",
            "Cookie or session tokens",
          ]}
        />
      </div>

      <div className="bg-bayyn-navy text-white rounded-2xl p-8 text-center">
        <h2 className="text-xl font-bold mb-2">The Invariant</h2>
        <p className="text-white/80 leading-relaxed">
          The <code className="bg-white/10 px-1 rounded">media_stored</code> field on every
          transcription job is always <code className="bg-white/10 px-1 rounded">false</code>. This
          is enforced in code and verified in tests. Bayyn cannot store media by design.
        </p>
      </div>
    </div>
  );
}
