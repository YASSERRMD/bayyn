import logging
import re
from typing import Any

import yt_dlp

from app.config import settings
from app.source_adapters.base import BaseSourceAdapter

logger = logging.getLogger(__name__)

YDL_BASE_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "socket_timeout": 30,
    "retries": 2,
}

YOUTUBE_DOMAINS = {
    "youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"
}


class YouTubeSourceAdapter(BaseSourceAdapter):
    """Adapter for YouTube URLs. Caption-first, audio fallback."""

    def validate_url(self) -> bool:
        from urllib.parse import urlparse
        host = urlparse(self.url).hostname or ""
        return host.lower() in YOUTUBE_DOMAINS

    def get_metadata(self) -> dict:
        opts = {**YDL_BASE_OPTS}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(self.url, download=False)

        duration = info.get("duration") or 0
        if duration > settings.max_video_duration_seconds:
            raise ValueError(
                f"Video duration {duration}s exceeds maximum "
                f"{settings.max_video_duration_seconds}s."
            )

        return {
            "title": info.get("title"),
            "duration": duration,
            "language": info.get("language") or settings.default_language,
            "uploader": info.get("uploader"),
        }

    def get_captions(self) -> list[dict]:
        opts = {
            **YDL_BASE_OPTS,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en", "en-US", "en-GB"],
            "subtitlesformat": "json3",
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(self.url, download=False)

        subtitles = info.get("subtitles", {})
        auto_subs = info.get("automatic_captions", {})

        lang_data = (
            subtitles.get("en")
            or subtitles.get("en-US")
            or subtitles.get("en-GB")
        )

        if lang_data:
            logger.info("Using manual English captions")
        else:
            lang_data = (
                auto_subs.get("en")
                or auto_subs.get("en-US")
                or auto_subs.get("en-GB")
            )
            if lang_data:
                logger.info("Using auto-generated English captions")

        if not lang_data:
            logger.info("No captions found, will fall back to Whisper")
            return []

        return self._parse_caption_data(lang_data, info)

    def _parse_caption_data(self, lang_data: list, info: dict) -> list[dict]:
        json3_entries = [e for e in lang_data if e.get("ext") == "json3"]
        if not json3_entries:
            vtt_entries = [e for e in lang_data if e.get("ext") == "vtt"]
            if vtt_entries:
                return self._fetch_vtt_captions(vtt_entries[0]["url"])
            return []

        entry = json3_entries[0]
        url = entry.get("url")
        if not url:
            return []

        import httpx
        try:
            resp = httpx.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("Failed to fetch json3 captions: %s", exc)
            return []

        segments = []
        for event in data.get("events", []):
            if "segs" not in event:
                continue
            start_ms = event.get("tStartMs", 0)
            dur_ms = event.get("dDurationMs", 0)
            text = "".join(s.get("utf8", "") for s in event["segs"])
            text = text.replace("\n", " ").strip()
            if not text or text == " ":
                continue
            segments.append({
                "start": start_ms / 1000.0,
                "end": (start_ms + dur_ms) / 1000.0,
                "text": text,
            })

        return segments

    def _fetch_vtt_captions(self, url: str) -> list[dict]:
        import httpx
        try:
            resp = httpx.get(url, timeout=15)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("Failed to fetch VTT: %s", exc)
            return []

        return _parse_vtt(resp.text)

    def get_audio_stream_url(self) -> str:
        opts = {
            **YDL_BASE_OPTS,
            "format": "bestaudio[ext=m4a]/bestaudio/best",
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(self.url, download=False)

        formats = info.get("formats", [])
        audio_formats = [
            f for f in formats
            if f.get("vcodec") == "none" and f.get("acodec") != "none"
        ]
        if not audio_formats:
            audio_formats = formats

        audio_formats.sort(key=lambda f: f.get("abr", 0) or 0, reverse=True)
        if not audio_formats:
            raise ValueError("No audio stream found for this video.")

        return audio_formats[0]["url"]


def _parse_vtt(vtt_text: str) -> list[dict]:
    segments = []
    lines = vtt_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        time_match = re.match(
            r"(\d{2}:\d{2}:\d{2}[.,]\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2}[.,]\d{3})", line
        )
        if time_match:
            start = _vtt_time_to_seconds(time_match.group(1))
            end = _vtt_time_to_seconds(time_match.group(2))
            text_lines = []
            i += 1
            while i < len(lines) and lines[i].strip():
                text_part = re.sub(r"<[^>]+>", "", lines[i]).strip()
                if text_part:
                    text_lines.append(text_part)
                i += 1
            text = " ".join(text_lines).strip()
            if text:
                segments.append({"start": start, "end": end, "text": text})
        else:
            i += 1
    return segments


def _vtt_time_to_seconds(ts: str) -> float:
    ts = ts.replace(",", ".")
    parts = ts.split(":")
    h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
    return h * 3600 + m * 60 + s
