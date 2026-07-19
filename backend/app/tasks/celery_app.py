from __future__ import annotations

from celery import Celery

from app.core.config import settings

# Celery application — configured to use Redis as broker and result backend
# Tasks are discovered automatically from the `tasks` package.
celery_app = Celery(
    "fiscalmind",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.document_tasks",   # Phase 3: document processing pipeline
        # "app.tasks.analysis_tasks", # Phase 7: financial analysis (future)
    ],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task behavior
    task_track_started=True,          # Enables STARTED state for long tasks
    task_acks_late=True,              # Acknowledge AFTER task completes (safer)
    worker_prefetch_multiplier=1,     # Prevents one worker hoarding all tasks

    # Retry configuration
    task_max_retries=3,
    task_default_retry_delay=60,      # Seconds between retries

    # Result expiry
    result_expires=3600,              # Results expire after 1 hour
)
