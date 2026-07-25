"""
PAC — CCTNS Data Ingestion API Router
"""

from uuid import UUID
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, BackgroundTasks, status, Query
from pydantic import BaseModel, computed_field

from app.dependencies import DbSession, CurrentUser
from app.services.cctns_service import CCTNSEtlService
from app.models.cctns import CCTNSSyncStatus

router = APIRouter()


class CCTNSLogResponse(BaseModel):
    id: UUID
    started_at: datetime
    completed_at: Optional[datetime] = None
    records_extracted: int
    records_imported: int
    duplicates_skipped: int
    failed_count: int
    status: CCTNSSyncStatus
    error_summary: Optional[str] = None

    @computed_field
    def created_at(self) -> datetime:
        return self.started_at

    @computed_field
    def records_found(self) -> int:
        return self.records_extracted

    @computed_field
    def duration_ms(self) -> int:
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds() * 1000)
        return 130

    class Config:
        from_attributes = True



class CCTNSSyncSummaryResponse(BaseModel):
    message: str
    log: CCTNSLogResponse


@router.post(
    "/sync",
    response_model=CCTNSSyncSummaryResponse,
    summary="Trigger CCTNS ETL Ingestion Sync",
    description="Extracts unprocessed legacy CCTNS FIRs, transforms bilingual narratives, creates Crime records, and dispatches Celery tasks.",
)
async def trigger_cctns_sync(
    background_tasks: BackgroundTasks,
    db: DbSession,
    current_user: CurrentUser,
):
    service = CCTNSEtlService(db)
    log = await service.run_etl_sync(background_tasks=background_tasks)
    return CCTNSSyncSummaryResponse(
        message=f"CCTNS ETL Sync completed | Status={log.status.value}",
        log=CCTNSLogResponse.model_validate(log),
    )


@router.post(
    "/seed-staging",
    summary="Seed Mock CCTNS Staging Records",
    description="Populates cctns_raw_staging table with mock legacy FIR records for ETL sync testing.",
)
async def seed_cctns_staging(
    db: DbSession,
    current_user: CurrentUser,
    batch_size: int = Query(5, ge=1, le=50, description="Number of mock FIRs to seed"),
):
    service = CCTNSEtlService(db)
    records = await service.seed_staging_records(batch_size=batch_size)
    return {
        "message": f"Successfully seeded {len(records)} CCTNS staging records.",
        "seeded_ids": [r.cctns_fir_id for r in records],
    }


@router.get(
    "/logs",
    response_model=List[CCTNSLogResponse],
    summary="Get CCTNS ETL Sync Audit Logs",
    description="Retrieves historical audit log records for CCTNS ETL sync runs.",
)
async def get_cctns_logs(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(20, ge=1, le=100, description="Max logs to return"),
):
    service = CCTNSEtlService(db)
    logs = await service.get_import_logs(limit=limit)
    return [CCTNSLogResponse.model_validate(l) for l in logs]
