"""
PAC — DNA Generation Service (Phase 2)

Orchestrates the full Crime DNA generation pipeline:

  1. create_pending()   → called synchronously during crime registration
                          Creates PENDING row with all available metadata
  2. generate()         → runs as a BackgroundTask
                          Calls ML Engine, stores embedding, marks COMPLETED
                          Retries up to MAX_RETRIES with exponential backoff
  3. reindex()          → triggered via API (supervisor+)
                          Resets a COMPLETED/FAILED record and re-generates

Time Intelligence:
  Derived from crime.occurred_at at generation time.
  Stored precomputed in crime_dna to avoid per-query derivation.

Design (ADR-004):
  Uses FastAPI BackgroundTasks — zero extra infrastructure.
  DB-backed PENDING status provides crash safety.
  Startup sweep in main.py re-queues any orphaned records.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import httpx

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.crime import Crime, CrimeMO
from app.models.crime_dna import DNAStatus
from app.repositories.dna_repo import DNARepository

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0          # seconds; doubles each attempt
MLENGINE_TIMEOUT = 30.0         # seconds per request


# ── Time Intelligence Helper ───────────────────────────────

def _compute_time_intelligence(occurred_at: datetime) -> dict:
    """
    Derive all time intelligence fields from occurred_at.
    Called once at generation time; results stored in crime_dna.

    Returns dict ready to splat into DNARepository.create_pending().
    """
    h = occurred_at.hour
    dow = occurred_at.weekday()          # 0=Mon … 6=Sun
    m = occurred_at.month

    is_night = h >= 21 or h < 6
    is_weekend = dow >= 5

    if 6 <= h < 12:
        slot = "morning"
    elif 12 <= h < 17:
        slot = "afternoon"
    elif 17 <= h < 21:
        slot = "evening"
    elif 21 <= h < 24:
        slot = "night"
    else:                                # 0:00–05:59
        slot = "late_night"

    return {
        "hour_of_day":      h,
        "day_of_week":      dow,
        "is_weekend":       is_weekend,
        "is_night":         is_night,
        "time_of_day_slot": slot,
        "month":            m,
    }


# ── DNA Service ────────────────────────────────────────────

class DNAService:
    """Handles Crime DNA generation, status tracking, and retry logic."""

    def __init__(self, db) -> None:
        # db can be an AsyncSession (normal use) or None (background use)
        self.db = db

    # ── Synchronous registration step ──────────────────────

    async def create_pending(
        self,
        crime: Crime,
        mo: Optional[CrimeMO] = None,
    ):
        """
        Called synchronously during crime registration (before HTTP response).

        Creates a PENDING CrimeDNA row with all metadata that's
        available immediately — no ML Engine call yet.

        Args:
            crime: The just-created Crime ORM object
            mo: The just-created CrimeMO ORM object (may be None)
        """
        repo = DNARepository(self.db)

        # Compute time intelligence from occurred_at
        time_intel = _compute_time_intelligence(crime.occurred_at)

        await repo.create_pending(
            crime_id=crime.id,
            crime_type=crime.crime_type.value if crime.crime_type else None,
            district=crime.district,
            police_station=crime.police_station,
            latitude=crime.latitude,
            longitude=crime.longitude,
            **time_intel,
        )

    # ── Background task (runs after HTTP response) ─────────

    async def generate(self, crime_id: UUID) -> None:
        """
        Background task: generate and persist Crime DNA embedding.

        Creates its own database session (request session is closed by
        the time this runs as a BackgroundTask).

        Retries up to MAX_RETRIES with exponential backoff.
        On exhaustion, marks status=FAILED (recoverable via /reindex endpoint).
        """
        async with AsyncSessionLocal() as session:
            repo = DNARepository(session)

            # ── Load crime + MO ─────────────────────────
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            from app.models.crime import Crime

            result = await session.execute(
                select(Crime)
                .options(selectinload(Crime.mo_features))
                .where(Crime.id == crime_id)
            )
            crime = result.scalar_one_or_none()

            if crime is None:
                logger.error(f"DNA generate: crime not found | crime_id={crime_id}")
                return

            mo_text = crime.mo_text
            if not mo_text:
                logger.warning(f"DNA generate: no mo_text | crime_id={crime_id} — skipping")
                await repo.mark_failed(crime_id, "No MO text to embed", retry_count=0)
                await session.commit()
                return

            # ── Mark PROCESSING ──────────────────────────
            await repo.mark_processing(crime_id)
            await session.commit()

            # ── Call ML Engine with retry ────────────────
            embedding = None
            last_error = ""

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    embedding = await _call_embed_endpoint(mo_text, crime_id)
                    break                          # success — exit retry loop

                except Exception as exc:
                    last_error = str(exc)
                    logger.warning(
                        f"DNA embed attempt {attempt}/{MAX_RETRIES} failed "
                        f"| crime_id={crime_id} | {exc}"
                    )
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(RETRY_BASE_DELAY ** attempt)

            # ── Store result ─────────────────────────────
            mo = crime.mo_features
            if embedding is not None:
                await repo.mark_completed(
                    crime_id,
                    embedding=embedding,
                    mo_text_embedded=mo_text,
                    crime_method=mo.crime_method   if mo else None,
                    target_type=mo.target_type     if mo else None,
                    weapon_used=mo.weapon_used     if mo else None,
                    tools_used=mo.tools_used       if mo else [],
                    planning_level=mo.planning_level if mo else None,
                    gang_involved=mo.gang_involved  if mo else False,
                    escape_method=mo.escape_method  if mo else None,
                    modus_operandi_tags=mo.modus_operandi_tags if mo else [],
                )
                logger.info(f"Crime DNA generated | crime_id={crime_id}")
            else:
                await repo.mark_failed(
                    crime_id,
                    error_message=f"ML Engine unavailable after {MAX_RETRIES} attempts: {last_error}",
                    retry_count=MAX_RETRIES,
                )
                logger.critical(
                    f"Crime DNA FAILED permanently | crime_id={crime_id} | {last_error}"
                )

            await session.commit()

    # ── Manual re-index ────────────────────────────────────

    async def reindex(self, crime_id: UUID) -> None:
        """
        Force re-generation of Crime DNA (supervisor+ endpoint).
        Resets the record to PENDING then re-runs generate().
        """
        repo = DNARepository(self.db)
        dna = await repo.reset_for_reindex(crime_id)
        if dna is None:
            from app.core.exceptions import NotFoundError
            raise NotFoundError("CrimeDNA", str(crime_id))
        await self.db.commit()
        # The caller (router) adds generate() as a BackgroundTask
        logger.info(f"Crime DNA reset to PENDING for reindex | crime_id={crime_id}")


# ── ML Engine HTTP Client ──────────────────────────────────

async def _call_embed_endpoint(
    mo_text: str,
    crime_id: UUID,
) -> list:
    """
    Call the ML Engine /embed endpoint.

    Returns L2-normalised 384-dim float list.
    Raises httpx.HTTPError or ValueError on failure.
    """
    url = f"{settings.MLENGINE_URL}/embed"
    payload = {
        "texts": [mo_text],
        "crime_ids": [str(crime_id)],
        "normalize": True,
    }

    async with httpx.AsyncClient(timeout=MLENGINE_TIMEOUT) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    embeddings = data.get("embeddings", [])
    if not embeddings or len(embeddings[0]) != 384:
        raise ValueError(
            f"ML Engine returned unexpected embedding shape: "
            f"len={len(embeddings[0]) if embeddings else 0}"
        )

    return embeddings[0]
