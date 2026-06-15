"""
Map internal exceptions to safe, user-facing messages.

Internal details (exception type, raw message, traceback) must only
appear in AuditLog — never in API responses or job.error_message.
"""
from __future__ import annotations

import logging
import re
import traceback
from typing import Optional

logger = logging.getLogger(__name__)

# ── User-facing message catalogue ─────────────────────────────────────────────

_NETWORK_ERRORS = (
    "urlopen error",
    "connection reset",
    "connection refused",
    "no address associated",
    "name or service not known",
    "temporary failure in name resolution",
    "httperror",
    "http error",
    "403",
    "404",
    "410",
    "yt-dlp",
    "unable to download",
    "this video is unavailable",
    "video unavailable",
    "private video",
    "members-only",
)

_AUDIO_ERRORS = (
    "ffmpeg",
    "no such file",
    "returncode",
    "audio extraction",
    "no audio",
    "format",
    "codec",
)

_TRANSCRIBE_ERRORS = (
    "whisper",
    "faster_whisper",
    "out of memory",
    "cuda",
    "ctranslate",
    "transcribe",
)

_DURATION_ERRORS = (
    "too long",
    "exceeds",
    "max_seconds",
    "videotoolong",
)

_CAPTION_ERRORS = (
    "no captions",
    "caption",
    "subtitle",
)


def classify_error(exc: Exception) -> str:
    """Return a short, user-safe error string for *exc*."""
    raw = f"{type(exc).__name__}: {exc}".lower()

    if any(k in raw for k in _DURATION_ERRORS):
        return "Video exceeds the maximum allowed length."

    if any(k in raw for k in _NETWORK_ERRORS):
        return "Could not fetch the video. Check the URL and try again."

    if any(k in raw for k in _AUDIO_ERRORS):
        return "Audio extraction failed. The video format may not be supported."

    if any(k in raw for k in _TRANSCRIBE_ERRORS):
        return "Speech recognition failed. Please try again later."

    if any(k in raw for k in _CAPTION_ERRORS):
        return "No captions found for this video."

    return "Transcription failed due to an unexpected error. Please try again."


def sanitize_for_audit(exc: Exception, *, max_len: int = 4096) -> str:
    """
    Return a detailed error string safe to store in AuditLog.details.
    Redacts filesystem paths and URLs so they are not leaked beyond the DB.
    """
    tb = traceback.format_exc()
    combined = f"{type(exc).__name__}: {exc}\n\n{tb}"
    combined = re.sub(r"https?://\S+", "[URL]", combined)
    combined = re.sub(r"/(?:tmp|var|home|usr|opt)/\S+", "[PATH]", combined)
    return combined[:max_len]


def build_audit_detail(exc: Exception, context: Optional[dict] = None) -> dict:
    """Build the dict stored in AuditLog.details for an error event."""
    detail: dict = {
        "exc_type": type(exc).__name__,
        "exc_summary": sanitize_for_audit(exc),
        "user_message": classify_error(exc),
    }
    if context:
        detail.update(context)
    return detail
