from __future__ import annotations
from typing import Any


def generate_txt(doc: Any, *, include_timestamps: bool = False, segments: list[Any] | None = None) -> str:
    """Return plain-text transcript.

    When include_timestamps=True, each segment is prefixed with [HH:MM:SS].
    Falls back to full_text if segments are unavailable.
    """
    if include_timestamps and segments:
        return _timestamped(segments)
    return doc.full_text


def _timestamped(segments: list[Any]) -> str:
    lines = []
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        ts = _format_hms(float(seg.start_seconds))
        lines.append(f"[{ts}] {text}")
    return "\n".join(lines)


def _format_hms(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
