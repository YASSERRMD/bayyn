from __future__ import annotations
from typing import Any


def generate_srt(segments: list[Any]) -> str:
    lines: list[str] = []
    index = 1
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        start = max(0.0, float(seg.start_seconds))
        end = float(seg.end_seconds)
        if end <= start:
            end = start + 0.001
        lines.append(str(index))
        lines.append(f"{_to_srt_time(start)} --> {_to_srt_time(end)}")
        lines.append(text)
        lines.append("")
        index += 1
    return "\n".join(lines)


def _to_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds % 1) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
