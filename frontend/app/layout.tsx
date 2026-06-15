import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Bayyn — Transcript, Not Media",
  description:
    "Paste a link. Get the transcript. Keep the knowledge, not the media. Bayyn stores only transcripts — never video or audio.",
  keywords: ["transcript", "YouTube", "privacy", "AI transcription", "captions"],
};

function Navbar() {
  return (
    <nav className="bg-bayyn-navy text-white shadow-sm">
      <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 group">
          <span className="text-bayyn-gold font-bold text-2xl tracking-tight">Bayyn</span>
          <span className="text-white/40 text-sm hidden sm:block">/ transcript</span>
        </Link>
        <div className="flex items-center gap-6 text-sm">
          <Link
            href="/history"
            className="text-white/80 hover:text-bayyn-gold transition-colors"
          >
            History
          </Link>
          <Link
            href="/privacy"
            className="text-white/80 hover:text-bayyn-gold transition-colors"
          >
            Privacy
          </Link>
        </div>
      </div>
    </nav>
  );
}

function Footer() {
  return (
    <footer className="border-t border-gray-200 bg-white mt-16">
      <div className="max-w-5xl mx-auto px-4 py-8 text-center text-sm text-gray-500">
        <p>
          <span className="text-bayyn-navy font-semibold">Bayyn</span> — Store knowledge, not
          media.
        </p>
        <p className="mt-1">
          Bayyn does not store video or audio. Only the transcript is saved.
        </p>
        <div className="mt-3 flex justify-center gap-4">
          <Link href="/privacy" className="hover:text-bayyn-navy transition-colors">
            Privacy Policy
          </Link>
          <Link href="/history" className="hover:text-bayyn-navy transition-colors">
            Transcript History
          </Link>
        </div>
      </div>
    </footer>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col">
        <Providers>
          <Navbar />
          <main className="flex-1">{children}</main>
          <Footer />
        </Providers>
      </body>
    </html>
  );
}
