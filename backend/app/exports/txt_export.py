from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.models.transcript_document import TranscriptDocument


def generate_txt(doc: Any) -> str:
    return doc.full_text
