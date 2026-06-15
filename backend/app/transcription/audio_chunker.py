from __future__ import annotations
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def chunk_audio(
    wav_path: Path,
    chunk_duration: int,
    temp_dir: Path,
) -> list[tuple[Path, float]]:
    """
    Split wav_path into sequential chunks of chunk_duration seconds using ffmpeg.
    Returns list of (chunk_path, start_offset_seconds) sorted by offset.
    The caller is responsible for deleting the chunks after use.
    """
    if not wav_path.exists():
        raise FileNotFoundError(f"WAV file not found: {wav_path}")

    chunks_dir = temp_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)

    pattern = str(chunks_dir / "chunk_%04d.wav")

    cmd = [
        "ffmpeg",
        "-i", str(wav_path),
        "-f", "segment",
        "-segment_time", str(chunk_duration),
        "-c", "copy",
        "-reset_timestamps", "1",
        pattern,
        "-y",
    ]

    logger.info("Splitting audio into %ds chunks", chunk_duration)
    result = subprocess.run(cmd, capture_output=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg chunking failed with code {result.returncode}")

    chunk_files = sorted(chunks_dir.glob("chunk_*.wav"))
    if not chunk_files:
        raise RuntimeError("ffmpeg produced no chunk files")

    chunks: list[tuple[Path, float]] = []
    for idx, path in enumerate(chunk_files):
        start_offset = float(idx * chunk_duration)
        chunks.append((path, start_offset))

    logger.info("Created %d audio chunks", len(chunks))
    return chunks


def delete_chunks(chunks: list[tuple[Path, float]]) -> None:
    """Delete chunk files produced by chunk_audio."""
    for path, _ in chunks:
        try:
            path.unlink(missing_ok=True)
        except Exception as exc:
            logger.warning("Failed to delete chunk %s: %s", path, type(exc).__name__)
