"""
PAC — Standalone Background Worker Tasks

Defines durable background tasks processed by the pac_worker container.
"""

import asyncio
import logging
from uuid import UUID
from typing import Dict, Any

from app.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.graph_db import get_graph_session
from app.services.dna_service import DNAService
from app.services.graph_service import GraphService
from app.services.behavior_service import BehaviorService
from app.services.prediction_service import PredictionService

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Utility helper to run async coroutines synchronously inside Celery worker threads."""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.task_generate_crime_dna", bind=True, max_retries=3, default_retry_delay=5)
def task_generate_crime_dna(self, crime_id_str: str) -> Dict[str, Any]:
    """Generate dense 384-dim Crime DNA embedding and extract MO features."""
    logger.info(f"[Celery Worker] Generating Crime DNA | crime_id={crime_id_str}")
    crime_id = UUID(crime_id_str)

    async def _async_dna():
        async with AsyncSessionLocal() as session:
            dna_service = DNAService(session)
            return await dna_service.generate(crime_id)

    try:
        _run_async(_async_dna())
        logger.info(f"[Celery Worker] Crime DNA generation completed | crime_id={crime_id_str}")
        return {"crime_id": crime_id_str, "status": "completed"}
    except Exception as exc:
        logger.error(f"[Celery Worker] Crime DNA generation failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(name="app.tasks.task_merge_graph_entity", bind=True, max_retries=3, default_retry_delay=5)
def task_merge_graph_entity(self, criminal_id_str: str, crime_id_str: str) -> Dict[str, Any]:
    """Merge criminal-crime co-offending relationship into Neo4j graph DB."""
    logger.info(f"[Celery Worker] Merging Neo4j Graph entity | criminal_id={criminal_id_str} crime_id={crime_id_str}")

    async def _async_graph():
        async with get_graph_session() as neo4j_session:
            async with AsyncSessionLocal() as db_session:
                service = GraphService(db_session, neo4j_session)
                return await service.sync_criminal_to_neo4j(UUID(criminal_id_str))

    try:
        _run_async(_async_graph())
        return {"criminal_id": criminal_id_str, "crime_id": crime_id_str, "status": "merged"}
    except Exception as exc:
        logger.error(f"[Celery Worker] Neo4j graph merge failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(name="app.tasks.task_recompute_behavior_profile", bind=True, max_retries=3, default_retry_delay=5)
def task_recompute_behavior_profile(self, criminal_id_str: str) -> Dict[str, Any]:
    """Recompute criminal MO consistency, operating radius, and temporal patterns."""
    logger.info(f"[Celery Worker] Recomputing Behaviour Profile | criminal_id={criminal_id_str}")
    criminal_id = UUID(criminal_id_str)

    async def _async_behavior():
        async with AsyncSessionLocal() as session:
            service = BehaviorService(session)
            return await service.generate_profile(criminal_id)

    try:
        profile = _run_async(_async_behavior())
        return {"criminal_id": criminal_id_str, "status": "computed"}
    except Exception as exc:
        logger.error(f"[Celery Worker] Behaviour profile calculation failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(name="app.tasks.task_recompute_prediction_profile", bind=True, max_retries=3, default_retry_delay=5)
def task_recompute_prediction_profile(self, criminal_id_str: str) -> Dict[str, Any]:
    """Recalculate criminal risk score, escalation index, and target type probabilities."""
    logger.info(f"[Celery Worker] Recalculating Prediction Profile | criminal_id={criminal_id_str}")
    criminal_id = UUID(criminal_id_str)

    async def _async_prediction():
        async with AsyncSessionLocal() as session:
            service = PredictionService(session)
            return await service.generate_prediction(criminal_id)

    try:
        prediction = _run_async(_async_prediction())
        return {"criminal_id": criminal_id_str, "status": "computed"}
    except Exception as exc:
        logger.error(f"[Celery Worker] Prediction profile calculation failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(name="app.tasks.task_cctns_periodic_sync", bind=True, max_retries=2, default_retry_delay=10)
def task_cctns_periodic_sync(self) -> Dict[str, Any]:
    """Periodic Celery Beat task to execute CCTNS ETL data ingestion sync."""
    logger.info("[Celery Beat] Executing periodic CCTNS ETL data ingestion sync...")

    async def _async_cctns():
        from app.services.cctns_service import CCTNSEtlService
        async with AsyncSessionLocal() as session:
            service = CCTNSEtlService(session)
            return await service.run_etl_sync()

    try:
        log = _run_async(_async_cctns())
        return {
            "status": log.status.value,
            "extracted": log.records_extracted,
            "imported": log.records_imported,
            "duplicates": log.duplicates_skipped,
        }
    except Exception as exc:
        logger.error(f"[Celery Beat] CCTNS periodic sync failed: {exc}")
        raise self.retry(exc=exc)
