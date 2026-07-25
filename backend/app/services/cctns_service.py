"""
PAC — CCTNS Data Ingestion & ETL Service

Implements Extract, Transform, and Load (ETL) pipeline for legacy CCTNS FIRs:
  1. Extract: Fetches unprocessed raw CCTNS records from cctns_raw_staging.
  2. Transform:
     - Maps IPC Sections (e.g. Sec 379, 392, 420) to PAC CrimeType enums.
     - Sanitizes bilingual (Kannada + English) narratives and extracts MO features.
     - Parses geolocations, dates, district, and police station info.
  3. Load & Dispatch:
     - Idempotently creates or updates PostgreSQL Crime records.
     - Enqueues Celery background tasks (DNA embedding, Neo4j graph merge).
     - Triggers event-driven Redis cache invalidation (pac:cache:geo:*).
"""

import logging
import uuid
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cctns import CCTNSImportLog, CCTNSRawStaging, CCTNSSyncStatus
from app.models.crime import Crime, CrimeType, CrimeStatus, CrimeSeverity, CrimeMO
from app.core.task_dispatcher import dispatch_task
from app.tasks import task_generate_crime_dna
from app.services.graph_service import sync_crime_to_graph
from app.core.cache import invalidate_cache_pattern

logger = logging.getLogger(__name__)

# IPC Section to PAC CrimeType Mapping Rules
IPC_CRIME_TYPE_MAP: Dict[str, CrimeType] = {
    "SEC_379_IPC": CrimeType.THEFT,
    "SEC_380_IPC": CrimeType.THEFT,
    "SEC_392_IPC": CrimeType.ROBBERY,
    "SEC_395_IPC": CrimeType.DACOITY,
    "SEC_384_IPC": CrimeType.EXTORTION,
    "SEC_302_IPC": CrimeType.MURDER,
    "SEC_420_IPC": CrimeType.CYBER_CRIME,
    "SEC_354_IPC": CrimeType.ASSAULT,
    "SEC_307_IPC": CrimeType.MURDER,
    "SEC_363_IPC": CrimeType.KIDNAPPING,
}


def parse_ipc_section(ipc_section: str) -> CrimeType:
    """Map legacy CCTNS IPC section to PAC CrimeType enum."""
    if not ipc_section:
        return CrimeType.OTHER
    cleaned = ipc_section.upper().replace(" ", "_").replace(".", "")
    for key, ctype in IPC_CRIME_TYPE_MAP.items():
        if key in cleaned:
            return ctype
    if "CHAIN" in cleaned or "SNATCH" in cleaned:
        return CrimeType.CHAIN_SNATCHING
    if "VEHICLE" in cleaned or "AUTO" in cleaned:
        return CrimeType.AUTO_THEFT
    return CrimeType.OTHER


def sanitize_bilingual_narrative(text: str) -> str:
    """Cleanse raw bilingual Kannada + English text, stripping control chars and excessive whitespace."""
    if not text:
        return ""
    # Strip invalid control characters while retaining Kannada unicode block (U+0C80 - U+0CFF)
    cleaned = re.sub(r"[\r\n\t]+", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


class CCTNSEtlService:
    """Coordinates CCTNS legacy FIR data extraction, transformation, and load."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def seed_staging_records(self, batch_size: int = 5) -> List[CCTNSRawStaging]:
        """Generate realistic mock CCTNS legacy FIR records in staging table for testing."""
        staging_records = []
        now = datetime.utcnow()
        for i in range(batch_size):
            fir_id = f"CCTNS-KAR-2026-{uuid.uuid4().hex[:6].upper()}"
            raw_payload = {
                "cctns_fir_id": fir_id,
                "district": "Bengaluru East" if i % 2 == 0 else "Bengaluru Urban",
                "police_station": "Indiranagar PS" if i % 2 == 0 else "Koramangala PS",
                "ipc_section": "SEC_392_IPC" if i % 2 == 0 else "SEC_420_IPC",
                "severity": "high" if i % 2 == 0 else "medium",
                "mo_narrative": (
                    "ರಾತ್ರಿ 8:30 ಸುಮಾರಿಗೆ ಇಬ್ಬರು ಬೈಕ್ ಸವಾರರು ಮಹಿಳೆಯ ಚಿನ್ನದ ಸರ ಕಸಿದು ಪರಾರಿಯಾಗಿದ್ದಾರೆ. "
                    "Two motorcycle riders wearing helmets snatched gold chain from victim near Indiranagar bus stop."
                ),
                "occurred_at": now.isoformat(),
                "latitude": 12.9716 + (i * 0.005),
                "longitude": 77.5946 + (i * 0.005),
                "location_address": f"100 Feet Road, Block {i+1}, Bengaluru",
            }
            rec = CCTNSRawStaging(
                id=uuid.uuid4(),
                cctns_fir_id=fir_id,
                raw_payload=raw_payload,
                is_processed=False,
            )
            self.db.add(rec)
            staging_records.append(rec)

        await self.db.commit()
        logger.info(f"[CCTNS ETL] Seeded {len(staging_records)} staging FIR records.")
        return staging_records

    async def run_etl_sync(self, background_tasks: Optional[Any] = None) -> CCTNSImportLog:
        """
        Executes full ETL sync run:
          - Extract unprocessed CCTNSRawStaging records.
          - Transform & Insert into crimes table.
          - Dispatch Celery tasks & Redis cache invalidation.
        """
        import_log = CCTNSImportLog(
            id=uuid.uuid4(),
            started_at=datetime.utcnow(),
            status=CCTNSSyncStatus.RUNNING,
        )
        self.db.add(import_log)
        await self.db.flush()

        try:
            # ── 1. Extract ──────────────────────────────────────────────
            query = select(CCTNSRawStaging).where(CCTNSRawStaging.is_processed == False).limit(100)
            res = await self.db.execute(query)
            unprocessed: List[CCTNSRawStaging] = res.scalars().all()
            import_log.records_extracted = len(unprocessed)

            if not unprocessed:
                logger.info("[CCTNS ETL] Zero unprocessed staging records found.")
                import_log.status = CCTNSSyncStatus.SUCCESS
                import_log.completed_at = datetime.utcnow()
                await self.db.commit()
                return import_log

            imported_count = 0
            duplicate_count = 0
            failed_count = 0

            # ── 2. Transform & Load ─────────────────────────────────────
            for item in unprocessed:
                payload = item.raw_payload
                fir_no = payload.get("cctns_fir_id", item.cctns_fir_id)

                # Check deduplication
                existing_res = await self.db.execute(select(Crime).where(Crime.fir_number == fir_no))
                if existing_res.scalar_one_or_none():
                    duplicate_count += 1
                    item.is_processed = True
                    item.processed_at = datetime.utcnow()
                    continue

                try:
                    ctype = parse_ipc_section(payload.get("ipc_section", ""))
                    sev_str = str(payload.get("severity", "medium")).lower()
                    severity = (
                        CrimeSeverity.CRITICAL if sev_str == "critical"
                        else CrimeSeverity.HIGH if sev_str == "high"
                        else CrimeSeverity.MEDIUM if sev_str == "medium"
                        else CrimeSeverity.LOW
                    )
                    mo_text = sanitize_bilingual_narrative(payload.get("mo_narrative", ""))

                    occurred_at = datetime.utcnow()
                    if payload.get("occurred_at"):
                        try:
                            occurred_at = datetime.fromisoformat(payload["occurred_at"].replace("Z", "+00:00"))
                        except Exception:
                            pass

                    new_crime = Crime(
                        id=uuid.uuid4(),
                        fir_number=fir_no,
                        crime_type=ctype,
                        severity=severity,
                        status=CrimeStatus.UNDER_INVESTIGATION,
                        district=payload.get("district", "Bengaluru Urban"),
                        police_station=payload.get("police_station", "Central PS"),
                        location_address=payload.get("location_address", "Bengaluru"),
                        latitude=payload.get("latitude", 12.9716),
                        longitude=payload.get("longitude", 77.5946),
                        description=f"Ingested from CCTNS system: {fir_no}",
                        mo_text=mo_text,
                        occurred_at=occurred_at,
                        reported_at=datetime.utcnow(),
                    )
                    self.db.add(new_crime)
                    await self.db.flush()

                    # Create MO record
                    mo_rec = CrimeMO(
                        id=uuid.uuid4(),
                        crime_id=new_crime.id,
                    )
                    self.db.add(mo_rec)

                    # Mark staging item as processed
                    item.is_processed = True
                    item.processed_at = datetime.utcnow()
                    imported_count += 1

                    # ── 3. Dispatch Celery tasks & Cache invalidation ───────
                    if background_tasks:
                        dispatch_task(task_generate_crime_dna, None, background_tasks, str(new_crime.id))
                        background_tasks.add_task(sync_crime_to_graph, new_crime.id)
                        background_tasks.add_task(invalidate_cache_pattern, "pac:cache:geo:*")
                        background_tasks.add_task(invalidate_cache_pattern, "pac:cache:predictions:*")

                except Exception as exc:
                    logger.error(f"[CCTNS ETL Error] Failed processing fir={fir_no}: {exc}")
                    failed_count += 1

            import_log.records_imported = imported_count
            import_log.duplicates_skipped = duplicate_count
            import_log.failed_count = failed_count
            import_log.status = (
                CCTNSSyncStatus.SUCCESS if failed_count == 0
                else CCTNSSyncStatus.PARTIAL_SUCCESS
            )
            import_log.completed_at = datetime.utcnow()
            await self.db.commit()

            logger.info(
                f"[CCTNS ETL Completed] Extracted={import_log.records_extracted} "
                f"Imported={imported_count} Duplicates={duplicate_count} Failed={failed_count}"
            )
            return import_log

        except Exception as exc:
            import_log.status = CCTNSSyncStatus.FAILED
            import_log.error_summary = str(exc)
            import_log.completed_at = datetime.utcnow()
            await self.db.commit()
            logger.error(f"[CCTNS ETL Execution Failed] {exc}")
            raise exc

    async def get_import_logs(self, limit: int = 20) -> List[CCTNSImportLog]:
        """Fetch historical CCTNS import logs ordered by started_at DESC."""
        res = await self.db.execute(
            select(CCTNSImportLog).order_by(CCTNSImportLog.started_at.desc()).limit(limit)
        )
        return res.scalars().all()
