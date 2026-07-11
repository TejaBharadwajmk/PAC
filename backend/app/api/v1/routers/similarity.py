"""
PAC — Similarity & DNA Intelligence Router (Phase 2)

Endpoints:
  POST  /api/v1/similarity/search           — Search by raw MO text
  GET   /api/v1/similarity/crime/{crime_id} — Find similar crimes for existing FIR
  GET   /api/v1/similarity/dna/{crime_id}   — Get DNA status + intelligence record
  POST  /api/v1/similarity/reindex/{id}     — Force DNA re-generation (supervisor+)
  GET   /api/v1/similarity/stats            — DNA pipeline health stats (analyst+)
"""

from uuid import UUID
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Query, Depends, status

from app.dependencies import DbSession, CurrentUser, require_roles
from app.models.user import UserRole
from app.schemas.dna import (
    CrimeDNAResponse,
    CrimeDNAStatusResponse,
    DNAPipelineStats,
    SimilaritySearchRequest,
    SimilaritySearchResponse,
)
from app.schemas.common import MessageResponse
from app.services.similarity_service import SimilarityService
from app.services.dna_service import DNAService
from app.repositories.dna_repo import DNARepository
from app.core.exceptions import NotFoundError

router = APIRouter()


@router.post(
    "/search",
    response_model=SimilaritySearchResponse,
    summary="Search similar crimes by MO text",
    description=(
        "Hybrid 3-phase similarity search:\n\n"
        "1. **Pre-filter** — SQL WHERE clause by crime_type, district, time\n"
        "2. **Vector ANN** — pgvector cosine similarity (all-MiniLM-L6-v2)\n"
        "3. **Feature scoring** — structured MO overlap + hybrid score\n\n"
        "Each result includes `explanation` and `matched_features` for full investigative explainability."
    ),
)
async def search_similar_crimes(
    request: SimilaritySearchRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    service = SimilarityService(db)
    return await service.search_by_text(request)


@router.get(
    "/crime/{crime_id}",
    response_model=SimilaritySearchResponse,
    summary="Find similar crimes for an existing FIR",
    description=(
        "Uses the pre-stored Crime DNA embedding to find behaviorally similar cases. "
        "Faster than /search (no ML Engine call needed). "
        "Returns 422 if Crime DNA is not yet generated."
    ),
)
async def find_similar_to_crime(
    crime_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(default=10, ge=1, le=50),
    min_similarity: float = Query(default=0.50, ge=0.0, le=1.0),
    district: Optional[str] = Query(default=None, description="Optional district filter"),
):
    service = SimilarityService(db)
    return await service.search_by_crime_id(
        crime_id=crime_id,
        limit=limit,
        min_similarity=min_similarity,
        district=district,
    )


@router.get(
    "/dna/{crime_id}",
    response_model=CrimeDNAResponse,
    summary="Get Crime DNA record and intelligence status",
    description=(
        "Returns the full Crime DNA record including:\n"
        "- Generation **status** (PENDING/PROCESSING/COMPLETED/FAILED)\n"
        "- All denormalized **intelligence fields** (MO, time, location)\n"
        "- Processing timestamps and retry count"
    ),
)
async def get_dna_record(
    crime_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    repo = DNARepository(db)
    dna = await repo.get_by_crime_id(crime_id)
    if dna is None:
        raise NotFoundError("CrimeDNA", str(crime_id))
    return dna


@router.get(
    "/dna/{crime_id}/status",
    response_model=CrimeDNAStatusResponse,
    summary="Lightweight DNA status check",
    description="Quick status check without full intelligence payload. Useful for polling.",
)
async def get_dna_status(
    crime_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    repo = DNARepository(db)
    dna = await repo.get_by_crime_id(crime_id)
    if dna is None:
        raise NotFoundError("CrimeDNA", str(crime_id))
    return dna


@router.post(
    "/reindex/{crime_id}",
    response_model=MessageResponse,
    summary="Force DNA re-generation (supervisor+)",
    description=(
        "Resets the Crime DNA record to PENDING and re-queues embedding generation. "
        "Use when DNA generation failed or when upgrading the embedding model."
    ),
    dependencies=[Depends(require_roles(UserRole.SUPERVISOR, UserRole.ADMIN))],
)
async def reindex_crime_dna(
    crime_id: UUID,
    background_tasks: BackgroundTasks,
    db: DbSession,
    current_user: CurrentUser,
):
    dna_service = DNAService(db)
    await dna_service.reindex(crime_id)
    # Launch background generation
    background_tasks.add_task(dna_service.generate, crime_id)
    return MessageResponse(
        message=f"Crime DNA reindexing queued for {crime_id}. "
                f"Status will change PENDING → PROCESSING → COMPLETED."
    )


@router.get(
    "/stats",
    response_model=DNAPipelineStats,
    summary="DNA pipeline health statistics (analyst+)",
    description=(
        "Returns counts of crimes by DNA status:\n"
        "- `pending` — awaiting processing\n"
        "- `processing` — currently running\n"
        "- `completed` — embedding ready for search\n"
        "- `failed` — generation failed (retryable via /reindex)\n"
        "- `completion_rate_pct` — % of crimes with completed DNA"
    ),
    dependencies=[Depends(require_roles(UserRole.ANALYST, UserRole.SUPERVISOR, UserRole.ADMIN))],
)
async def dna_pipeline_stats(
    db: DbSession,
    current_user: CurrentUser,
):
    repo = DNARepository(db)
    stats = await repo.get_pipeline_stats()
    return DNAPipelineStats(**stats)
