from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.models.transcript_segment import TranscriptSegment


def generate_srt(segments: list[Any]) -> str:
    lines = []
    for i, seg in enumerate(segments, start=1):
        start_ts = _seconds_to_srt_time(float(seg.start_seconds))
        end_ts = _seconds_to_srt_time(float(seg.end_seconds))
        lines.append(str(i))
        lines.append(f"{start_ts} --> {end_ts}")
        lines.append(seg.text.strip())
        lines.append("")
    return "\n".join(lines)


def _seconds_to_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds % 1) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
