"""
PAC — DNA & Similarity Schemas (Pydantic v2)

Covers:
  - CrimeDNA status response
  - Similarity search request + result
  - DNA pipeline statistics
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.models.crime_dna import DNAStatus
from app.models.crime import CrimeType


# ── CrimeDNA Response ──────────────────────────────────────

class CrimeDNAResponse(BaseModel):
    """Full DNA record response including status and intelligence fields."""
    id: UUID
    crime_id: UUID

    # Status
    status: DNAStatus
    status_message: Optional[str] = None
    retry_count: int = 0

    # Semantic
    model_name: str
    mo_text_embedded: Optional[str] = None

    # Structured MO
    crime_type: Optional[str] = None
    crime_method: Optional[str] = None
    target_type: Optional[str] = None
    weapon_used: Optional[str] = None
    tools_used: List[str] = Field(default_factory=list)
    planning_level: Optional[str] = None
    gang_involved: bool = False
    escape_method: Optional[str] = None
    modus_operandi_tags: List[str] = Field(default_factory=list)

    # Time intelligence
    hour_of_day: Optional[int] = None
    day_of_week: Optional[int] = None
    is_weekend: Optional[bool] = None
    is_night: Optional[bool] = None
    time_of_day_slot: Optional[str] = None
    month: Optional[int] = None

    # Location
    district: Optional[str] = None
    police_station: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Timestamps
    generated_at: Optional[datetime] = None
    processing_started_at: Optional[datetime] = None
    processing_failed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "protected_namespaces": (),   # allow model_name field
    }


class CrimeDNAStatusResponse(BaseModel):
    """Lightweight DNA status check response."""
    crime_id: UUID
    status: DNAStatus
    status_message: Optional[str] = None
    retry_count: int = 0
    generated_at: Optional[datetime] = None
    processing_started_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Similarity Search ──────────────────────────────────────

class SimilaritySearchRequest(BaseModel):
    """
    Request body for POST /similarity/search.

    Phase 1 (pre-filter): crime_type, district, time_of_day_slot
    Phase 2 (ANN): query_text embedded → cosine similarity
    Phase 3 (feature): hybrid score + explanation
    """
    query_text: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="MO narrative text to find similar crimes for",
    )
    # Pre-filter options
    crime_type: Optional[CrimeType] = Field(
        None, description="Restrict results to this crime type"
    )
    district: Optional[str] = Field(
        None, description="Restrict results to this district"
    )
    time_of_day_slot: Optional[str] = Field(
        None, description="Filter by time slot: morning/afternoon/evening/night/late_night"
    )
    # Search options
    limit: int = Field(default=10, ge=1, le=50, description="Max results to return")
    min_similarity: float = Field(
        default=0.50, ge=0.0, le=1.0,
        description="Minimum hybrid similarity score threshold"
    )


class SimilarityResult(BaseModel):
    """
    A single crime result from similarity search.

    Includes both the hybrid score and its individual components
    for full explainability (ADR-005).
    """
    # Crime identity
    crime_id: UUID
    fir_number: str
    crime_type: str
    severity: str
    status: str
    district: str
    police_station: str
    occurred_at: datetime
    mo_text: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Scores — all from 0.0 to 1.0
    similarity_score: float = Field(
        description="Hybrid score: 0.70×semantic + 0.30×feature"
    )
    semantic_similarity: float = Field(
        description="Cosine similarity of MO text embeddings"
    )
    feature_similarity: float = Field(
        description="Structured MO feature overlap score"
    )

    # Explainability
    matched_features: List[str] = Field(
        default_factory=list,
        description="List of MO features that matched: crime_method, target_type, etc.",
    )
    explanation: str = Field(
        description="Human-readable explanation of why crimes are similar"
    )

    # DNA intelligence fields (for display)
    crime_method: Optional[str] = None
    target_type: Optional[str] = None
    planning_level: Optional[str] = None
    gang_involved: bool = False
    time_of_day_slot: Optional[str] = None


class SimilaritySearchResponse(BaseModel):
    """Response envelope for similarity search results."""
    query_text: Optional[str] = None           # set for text-based search
    source_crime_id: Optional[UUID] = None     # set for crime-id-based search
    source_fir_number: Optional[str] = None
    results: List[SimilarityResult]
    total_candidates_scanned: int = Field(
        description="Number of COMPLETED DNA records searched before ranking"
    )
    filters_applied: dict = Field(default_factory=dict)


# ── DNA Pipeline Stats ─────────────────────────────────────

class DNAPipelineStats(BaseModel):
    """Admin view of the DNA generation pipeline health."""
    total_crimes: int
    pending: int
    processing: int
    completed: int
    failed: int
    completion_rate_pct: float
    avg_generation_time_ms: Optional[float] = None
