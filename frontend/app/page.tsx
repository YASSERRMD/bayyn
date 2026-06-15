import { Shield, Zap, FileText, Lock } from "lucide-react";
import { UrlForm } from "@/components/url-form";

function FeatureCard({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <div className="flex flex-col items-center text-center p-6 rounded-xl bg-white border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
      <div className="w-12 h-12 rounded-full bg-bayyn-navy/10 flex items-center justify-center mb-4">
        <Icon className="w-6 h-6 text-bayyn-navy" />
      </div>
      <h3 className="font-semibold text-bayyn-navy mb-2">{title}</h3>
      <p className="text-sm text-gray-600 leading-relaxed">{description}</p>
    </div>
  );
}

export default function HomePage() {
  return (
    <div className="min-h-screen bg-bayyn-bg">
      <section className="relative py-20 px-4 overflow-hidden">
        <div
          className="absolute inset-0 opacity-5"
          style={{
            backgroundImage:
              "radial-gradient(circle at 20% 50%, #1B2A4A 0%, transparent 50%), radial-gradient(circle at 80% 20%, #C5A55A 0%, transparent 50%)",
          }}
        />
        <div className="relative max-w-3xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-bayyn-navy/10 text-bayyn-navy rounded-full px-4 py-1.5 text-sm font-medium mb-6">
            <Shield className="w-4 h-4" />
            Privacy-first transcription
          </div>

          <h1 className="text-5xl sm:text-6xl font-bold text-bayyn-navy mb-4 leading-tight">
            Paste a link.
            <br />
            <span className="text-bayyn-gold">Get the transcript.</span>
          </h1>

          <p className="text-xl text-gray-600 mb-3 max-w-xl mx-auto">
            Keep the knowledge, not the media.
          </p>
          <p className="text-sm text-gray-500 mb-10 max-w-lg mx-auto">
            Bayyn extracts captions or transcribes audio temporarily, stores only the text, and
            discards all media immediately.
          </p>

          <div className="max-w-2xl mx-auto">
            <UrlForm />
          </div>

          <div className="mt-6 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-gray-500">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              No video stored
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              No audio stored
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-bayyn-gold" />
              Phase 1: YouTube supported
            </span>
          </div>
        </div>
      </section>

      <section className="py-16 px-4 bg-white">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl font-bold text-bayyn-navy text-center mb-3">
            How Bayyn Works
          </h2>
          <p className="text-gray-500 text-center mb-10 max-w-xl mx-auto">
            A two-strategy pipeline designed around your privacy.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <FeatureCard
              icon={Zap}
              title="Caption-First"
              description="Bayyn always tries to use existing captions — fast, accurate, and requires no audio processing."
            />
            <FeatureCard
              icon={FileText}
              title="Whisper Fallback"
              description="When captions aren't available, audio is transcribed temporarily via faster-whisper and immediately discarded."
            />
            <FeatureCard
              icon={Lock}
              title="Store Knowledge Only"
              description="Only the transcript text and metadata are saved. Video files, audio files, and thumbnails are never stored."
            />
            <FeatureCard
              icon={Shield}
              title="Export Freely"
              description="Export your transcript as plain text, SRT subtitles, or a Word document — generated live from the database."
            />
          </div>
        </div>
      </section>

      <section className="py-16 px-4">
        <div className="max-w-2xl mx-auto bg-bayyn-navy rounded-2xl p-8 text-center text-white">
          <div className="text-bayyn-gold text-4xl mb-4">🔒</div>
          <h2 className="text-2xl font-bold mb-3">Privacy Commitment</h2>
          <p className="text-white/80 leading-relaxed">
            Bayyn does not store video or audio. Only the transcript is saved. Temporary processing
            files are deleted immediately after transcription completes — whether it succeeds or
            fails.
          </p>
          <div className="mt-6 inline-flex gap-4 text-sm">
            <a
              href="/privacy"
              className="text-bayyn-gold hover:underline"
            >
              Read our Privacy Policy →
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}
