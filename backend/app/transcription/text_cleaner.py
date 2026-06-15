from __future__ import annotations
import re

_REPEATED_WORD = re.compile(r'\b(\w+)(?:\s+\1)+\b', re.IGNORECASE)
_MULTI_SPACE = re.compile(r'  +')

# Standalone meaningless fillers at word boundaries (whole-segment or boundary anchors)
_FILLER_ONLY = re.compile(
    r'(?<![a-zA-Z])(um+|uh+|hmm+|err?|ahh?|ehh?|mmm?)(?![a-zA-Z])',
    re.IGNORECASE,
)

_MULTI_PUNCT = re.compile(r'([.!?,;:]){2,}')
_SPACE_BEFORE_PUNCT = re.compile(r'\s+([.,!?;:])')
_MISSING_SPACE_AFTER_PUNCT = re.compile(r'([.!?,;:])([^\s\d])')


def remove_filler_artifacts(text: str) -> str:
    """Remove repeated consecutive words and standalone vocal-filler artifacts."""
    text = _REPEATED_WORD.sub(r'\1', text)
    text = _FILLER_ONLY.sub('', text)
    text = _MULTI_SPACE.sub(' ', text).strip()
    return text


def normalize_punctuation(text: str) -> str:
    """Collapse duplicate punctuation marks and fix spacing around punctuation."""
    text = _MULTI_PUNCT.sub(r'\1', text)
    text = _SPACE_BEFORE_PUNCT.sub(r'\1', text)
    text = _MISSING_SPACE_AFTER_PUNCT.sub(r'\1 \2', text)
    text = _MULTI_SPACE.sub(' ', text).strip()
    return text
