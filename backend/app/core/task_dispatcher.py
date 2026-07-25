"""
PAC — Task Dispatcher (Hybrid Fallback Dispatcher)

Dispatches background jobs either to Celery workers (for distributed execution)
or to FastAPI inline BackgroundTasks (if Celery is disabled or offline).
"""

import logging
from typing import Callable, Any, Optional
from fastapi import BackgroundTasks

from app.config import settings

logger = logging.getLogger(__name__)


def dispatch_task(
    celery_task: Any,
    fallback_async_func: Callable,
    background_tasks: Optional[BackgroundTasks] = None,
    *args,
    **kwargs,
) -> bool:
    """
    Dispatch a background task.

    Attempts Celery worker enqueue first if settings.CELERY_ENABLED is True.
    Falls back to FastAPI BackgroundTasks if Celery is disabled or unavailable.

    Args:
        celery_task: The Celery task object (e.g. task_generate_crime_dna).
        fallback_async_func: The async function for inline execution (e.g. DNAService.generate).
        background_tasks: FastAPI BackgroundTasks instance from the route.
        *args, **kwargs: Arguments passed to the task.

    Returns:
        True if enqueued to Celery, False if handled by inline BackgroundTasks.
    """
    if settings.CELERY_ENABLED and celery_task is not None:
        try:
            # Enqueue to Celery worker queue
            celery_task.delay(*[str(a) if hasattr(a, "hex") else a for a in args], **kwargs)
            logger.info(f"Task {celery_task.name!r} enqueued to Celery worker successfully")
            return True
        except Exception as exc:
            logger.warning(f"Celery enqueue failed ({exc}). Falling back to FastAPI BackgroundTasks.")

    # Fallback to inline FastAPI BackgroundTasks
    if background_tasks is not None:
        background_tasks.add_task(fallback_async_func, *args, **kwargs)
        logger.info(f"Task {fallback_async_func.__name__!r} added to FastAPI inline BackgroundTasks")
    else:
        logger.warning(f"No BackgroundTasks provided; task {fallback_async_func.__name__!r} skipped")

    return False
