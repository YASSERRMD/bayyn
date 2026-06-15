import html
import re


def normalize_segments(segments: list[dict]) -> list[dict]:
    """Normalize raw caption segments: clean text, merge short gaps, deduplicate."""
    cleaned = []
    for seg in segments:
        text = _clean_caption_text(seg.get("text", ""))
        if not text:
            continue
        cleaned.append({
            "start": float(seg.get("start", 0)),
            "end": float(seg.get("end", 0)),
            "text": text,
            "confidence": seg.get("confidence"),
            "speaker": seg.get("speaker"),
        })

    if not cleaned:
        return []

    merged = _merge_consecutive_duplicates(cleaned)
    return merged


def _clean_caption_text(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


def _merge_consecutive_duplicates(segments: list[dict]) -> list[dict]:
    result = []
    for seg in segments:
        if result and result[-1]["text"].strip() == seg["text"].strip():
            result[-1]["end"] = seg["end"]
        else:
            result.append(dict(seg))
    return result


def captions_to_full_text(segments: list[dict]) -> str:
    return " ".join(s["text"].strip() for s in segments if s.get("text"))
