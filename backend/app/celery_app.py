"""
PAC — Celery Task Queue Application

Initializes the Celery application using Redis as the message broker
and result backend. Enables durable, non-blocking background execution
for compute-heavy PAC intelligence operations.
"""

import logging
from celery import Celery
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Celery app instance
celery_app = Celery(
    "pac_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Celery Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,  # Re-queue task if worker crashes during execution
    worker_prefetch_multiplier=1,  # Prevent single worker from hoarding tasks
    result_expires=3600,  # Expire task results after 1 hour
    beat_schedule={
        "cctns-periodic-etl-sync": {
            "task": "app.tasks.task_cctns_periodic_sync",
            "schedule": 300.0,  # Run every 5 minutes
        },
    },
)

# Autodiscover tasks from app.tasks module
celery_app.autodiscover_tasks(["app"])
