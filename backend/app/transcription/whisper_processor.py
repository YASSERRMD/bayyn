import logging
import os
import subprocess
import uuid
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

FFMPEG_AUDIO_ARGS = [
    "-vn",
    "-acodec", "pcm_s16le",
    "-ar", "16000",
    "-ac", "1",
    "-f", "wav",
]


def transcribe_audio(
    audio_stream_url: str, temp_dir: Path, job_uuid: uuid.UUID
) -> tuple[list[dict], str]:
    """
    Transcribe audio from a stream URL using faster-whisper.
    Returns (segments, detected_language).
    Never stores the original audio stream URL in logs.
    """
    try:
        return _transcribe_via_pipe(temp_dir)
    except Exception as pipe_exc:
        logger.info("Pipe transcription failed, trying temp file: %s", type(pipe_exc).__name__)
        return _transcribe_via_temp_file(audio_stream_url, temp_dir)


def _build_ffmpeg_pipe_cmd(audio_stream_url: str) -> list[str]:
    return [
        "ffmpeg",
        "-i", audio_stream_url,
        *FFMPEG_AUDIO_ARGS,
        "pipe:1",
    ]


def _transcribe_via_pipe(temp_dir: Path) -> tuple[list[dict], str]:
    raise NotImplementedError("Pure pipe not yet supported — using temp file path")


def _transcribe_via_temp_file(audio_stream_url: str, temp_dir: Path) -> tuple[list[dict], str]:
    wav_path = temp_dir / "audio.wav"

    cmd = [
        "ffmpeg",
        "-i", audio_stream_url,
        *FFMPEG_AUDIO_ARGS,
        str(wav_path),
        "-y",
    ]

    logger.info("Running ffmpeg to temp file in job dir")
    result = subprocess.run(
        cmd,
        capture_output=True,
        timeout=600,
    )

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed with code {result.returncode}")

    if not wav_path.exists():
        raise RuntimeError("ffmpeg produced no output file")

    file_size = wav_path.stat().st_size
    logger.info("Audio prepared size_bytes=%d", file_size)

    use_chunked = wav_path.stat().st_size > 0 and _should_chunk(wav_path)
    if use_chunked:
        segments, detected_language = _transcribe_chunked(wav_path, temp_dir)
    else:
        segments, detected_language = _run_whisper(wav_path)

    try:
        wav_path.unlink()
        logger.info("Deleted temp audio file immediately after transcription")
    except Exception as exc:
        logger.warning("Failed to delete temp audio: %s", type(exc).__name__)

    return segments, detected_language


def _should_chunk(wav_path: Path) -> bool:
    """Estimate audio duration from file size; return True if chunking is warranted."""
    # PCM s16le 16kHz mono: 16000 samples/s * 2 bytes/sample = 32000 bytes/s
    bytes_per_second = 32000
    estimated_seconds = wav_path.stat().st_size / bytes_per_second
    return estimated_seconds > settings.chunk_threshold_seconds


def _transcribe_chunked(wav_path: Path, temp_dir: Path) -> tuple[list[dict], str]:
    """Split wav into chunks, transcribe each, offset timestamps, merge results."""
    from app.transcription.audio_chunker import chunk_audio, delete_chunks

    chunks = chunk_audio(wav_path, settings.chunk_duration_seconds, temp_dir)
    all_segments: list[dict] = []
    detected_language = "en"

    for chunk_path, start_offset in chunks:
        try:
            chunk_segs, chunk_lang = _run_whisper(chunk_path)
            if chunk_segs:
                detected_language = chunk_lang
            for seg in chunk_segs:
                all_segments.append({
                    **seg,
                    "start": seg["start"] + start_offset,
                    "end": seg["end"] + start_offset,
                })
            logger.info("Chunk offset=%.0fs segments=%d", start_offset, len(chunk_segs))
        except Exception as exc:
            logger.warning(
                "Chunk at offset=%.0fs failed: %s — skipping",
                start_offset,
                type(exc).__name__,
            )

    delete_chunks(chunks)
    logger.info("Chunked transcription complete total_segments=%d", len(all_segments))
    return all_segments, detected_language


def _run_whisper(wav_path: Path) -> tuple[list[dict], str]:
    from faster_whisper import WhisperModel
    from app.transcription.language_detector import detect_from_whisper_info

    model_size = settings.whisper_model
    logger.info("Loading Whisper model=%s", model_size)

    model = WhisperModel(model_size, device="auto", compute_type="int8")

    segments_iter, info = model.transcribe(
        str(wav_path),
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )

    detected_language = detect_from_whisper_info(
        info.language, getattr(info, "language_probability", 1.0)
    )
    logger.info(
        "Whisper detected language=%s probability=%.2f normalized=%s",
        info.language,
        getattr(info, "language_probability", 1.0),
        detected_language,
    )

    results = []
    for seg in segments_iter:
        results.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
            "confidence": getattr(seg, "avg_logprob", None),
        })

    logger.info("Whisper produced segments=%d", len(results))
    return results, detected_language
