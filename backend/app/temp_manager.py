import hashlib
import logging
import os
import shutil
import time
import uuid
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class TempManager:
    """Manages per-job temporary directories. Ensures cleanup on success and failure."""

    @staticmethod
    def _base_dir() -> Path:
        return Path(settings.temp_dir)

    @staticmethod
    def _hash_path(path: Path) -> str:
        return hashlib.sha256(str(path).encode()).hexdigest()[:16]

    @classmethod
    def create_job_dir(cls, job_id: uuid.UUID) -> Path:
        job_dir = cls._base_dir() / str(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("Created temp dir hash=%s", cls._hash_path(job_dir))
        return job_dir

    @classmethod
    def cleanup_job_dir(cls, job_id: uuid.UUID, reason: str = "completed") -> bool:
        job_dir = cls._base_dir() / str(job_id)
        path_hash = cls._hash_path(job_dir)
        if not job_dir.exists():
            return True
        try:
            shutil.rmtree(job_dir)
            logger.info("Cleaned temp dir hash=%s reason=%s", path_hash, reason)
            return True
        except Exception as exc:
            logger.error("Failed to clean temp dir hash=%s: %s", path_hash, exc)
            return False

    @classmethod
    def startup_cleanup(cls) -> None:
        base = cls._base_dir()
        if not base.exists():
            base.mkdir(parents=True, exist_ok=True)
            return
        cutoff = time.time() - 3600
        for child in base.iterdir():
            if child.is_dir() and child.stat().st_mtime < cutoff:
                try:
                    shutil.rmtree(child)
                    logger.info("Startup cleanup removed stale dir hash=%s", cls._hash_path(child))
                except Exception as exc:
                    logger.warning("Startup cleanup failed for hash=%s: %s", cls._hash_path(child), exc)

    @classmethod
    def get_job_dir(cls, job_id: uuid.UUID) -> Path:
        return cls._base_dir() / str(job_id)
