from __future__ import annotations

DEFAULT_LANGUAGE = "en"

_KNOWN_LANGUAGES: frozenset[str] = frozenset([
    "en", "es", "fr", "de", "pt", "it", "nl", "pl", "ru", "zh",
    "ja", "ko", "ar", "hi", "tr", "sv", "da", "fi", "no", "cs",
    "ro", "uk", "el", "he", "id", "vi", "th", "hu", "sk", "bg",
])


def normalize_language_code(code: str) -> str:
    """Return ISO 639-1 two-letter code from any BCP-47 tag (e.g. en-US -> en)."""
    if not code:
        return DEFAULT_LANGUAGE
    base = code.lower().split("-")[0].split("_")[0].strip()
    return base if base else DEFAULT_LANGUAGE


def detect_from_caption_keys(available_keys: list[str]) -> str:
    """Return the first recognized language code found in caption key list."""
    for key in available_keys:
        normalized = normalize_language_code(key)
        if normalized in _KNOWN_LANGUAGES:
            return normalized
    return DEFAULT_LANGUAGE


def detect_from_whisper_info(language: str, language_probability: float) -> str:
    """Return normalized language from Whisper info, falling back to default if uncertain."""
    if language_probability < 0.5:
        return DEFAULT_LANGUAGE
    return normalize_language_code(language)
