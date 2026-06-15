from app.models.transcript_document import TranscriptDocument


def generate_txt(doc: TranscriptDocument) -> str:
    return doc.full_text
