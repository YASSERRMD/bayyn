from celery import Celery

from app.config import settings

celery_app = Celery(
    "bayyn",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.transcription_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.job_timeout_seconds,
    task_soft_time_limit=settings.job_timeout_seconds - 60,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    result_expires=3600,
    beat_schedule={
        "cleanup-stale-temp-dirs": {
            "task": "app.workers.transcription_tasks.cleanup_stale_temp_dirs",
            "schedule": 1800.0,
        },
    },
)
