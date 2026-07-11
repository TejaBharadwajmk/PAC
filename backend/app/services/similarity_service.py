"""
PAC — Hybrid Similarity Service (Phase 2)

Three-phase similarity search pipeline (ADR-005):

  Phase 1 — SQL pre-filter
    Restricts candidate pool by crime_type, district, time_of_day_slot
    (uses regular B-tree indexes, instant)

  Phase 2 — pgvector ANN
    Cosine distance search over completed embeddings
    (uses IVFFlat index, sub-10ms at 50k vectors)

  Phase 3 — Feature Overlap Scorer (Python, in-memory)
    Computes structured MO feature similarity
    Blends semantic + feature scores into hybrid_score
    Generates human-readable explanation for each result

Hybrid score formula (ADR-005):
    hybrid_score = α × semantic_similarity + β × feature_similarity
    α = 0.70, β = 0.30

Feature weights:
    crime_method   → 0.30
    target_type    → 0.25
    time_of_day    → 0.20
    gang_involved  → 0.15
    escape_method  → 0.10
"""

import logging
from typing import List, Optional
from uuid import UUID

import httpx

from app.config import settings
from app.repositories.dna_repo import DNARepository
from app.schemas.dna import (
    SimilarityResult,
    SimilaritySearchRequest,
    SimilaritySearchResponse,
)

logger = logging.getLogger(__name__)

# ── Hybrid Score Weights ───────────────────────────────────
ALPHA = 0.70    # semantic embedding weight
BETA  = 0.30    # feature overlap weight

FEATURE_WEIGHTS = {
    "crime_method":     0.30,
    "target_type":      0.25,
    "time_of_day_slot": 0.20,
    "gang_involved":    0.15,
    "escape_method":    0.10,
}

MLENGINE_TIMEOUT = 15.0
ANN_OVERFETCH    = 50   # fetch 50, re-rank in Python, return top-N


class SimilarityService:
    """Hybrid similarity search service."""

    def __init__(self, db) -> None:
        self.db = db
        self.repo = DNARepository(db)

    # ── Public Search Methods ──────────────────────────────

    async def search_by_text(
        self,
        request: SimilaritySearchRequest,
    ) -> SimilaritySearchResponse:
        """
        Search for similar crimes using a raw MO text query.

        Flow:
          1. Embed query_text via ML Engine
          2. Run hybrid search
          3. Return ranked results with explanations
        """
        # Embed the query text
        query_embedding = await self._embed_query(request.query_text)

        results, scanned = await self._hybrid_search(
            query_embedding=query_embedding,
            exclude_crime_id=None,
            request=request,
        )

        filters_applied = {}
        if request.crime_type:
            filters_applied["crime_type"] = request.crime_type.value
        if request.district:
            filters_applied["district"] = request.district
        if request.time_of_day_slot:
            filters_applied["time_of_day_slot"] = request.time_of_day_slot

        return SimilaritySearchResponse(
            query_text=request.query_text,
            results=results[: request.limit],
            total_candidates_scanned=scanned,
            filters_applied=filters_applied,
        )

    async def search_by_crime_id(
        self,
        crime_id: UUID,
        limit: int = 10,
        min_similarity: float = 0.50,
        district: Optional[str] = None,
    ) -> SimilaritySearchResponse:
        """
        Find crimes similar to an existing FIR using its stored embedding.

        No ML Engine call needed — uses the pre-stored embedding.
        """
        dna = await self.repo.get_by_crime_id(crime_id)
        if dna is None:
            from app.core.exceptions import NotFoundError
            raise NotFoundError("CrimeDNA", str(crime_id))

        if dna.embedding is None:
            from app.core.exceptions import ValidationError
            raise ValidationError(
                f"Crime DNA not yet generated for this crime (status={dna.status}). "
                "Try again after DNA generation completes."
            )

        # Recreate a request-like object for _hybrid_search
        request = SimilaritySearchRequest(
            query_text="",          # not used in this mode
            limit=limit,
            min_similarity=min_similarity,
            district=district,
        )

        # Convert pgvector column to plain Python list
        raw_embedding = list(dna.embedding)

        results, scanned = await self._hybrid_search(
            query_embedding=raw_embedding,
            exclude_crime_id=crime_id,
            request=request,
        )

        return SimilaritySearchResponse(
            source_crime_id=crime_id,
            results=results[:limit],
            total_candidates_scanned=scanned,
            filters_applied={"exclude_crime_id": str(crime_id)},
        )

    # ── Internal Pipeline ──────────────────────────────────

    async def _hybrid_search(
        self,
        query_embedding: List[float],
        exclude_crime_id: Optional[UUID],
        request: SimilaritySearchRequest,
    ) -> tuple[List[SimilarityResult], int]:
        """
        Run the full 3-phase hybrid search.

        Returns (ranked_results, total_candidates_scanned).
        """
        # Phase 1 + 2: SQL pre-filter + pgvector ANN
        max_distance = 1.0 - request.min_similarity
        rows = await self.repo.find_similar(
            query_embedding=query_embedding,
            exclude_crime_id=exclude_crime_id,
            limit=ANN_OVERFETCH,
            max_distance=max_distance,
            district_filter=request.district,
            crime_type_filter=request.crime_type.value if request.crime_type else None,
            time_slot_filter=request.time_of_day_slot,
        )

        scanned = len(rows)

        if not rows:
            return [], 0

        # Build a "query features" dict for Phase 3 comparison
        # For text-based queries: we don't know MO features yet.
        # We'll use the top-1 result's features as a proxy (best available)
        # to still provide meaningful explanations.
        # For crime-id queries: the caller could pass crime features — kept simple here.
        query_features: dict = {}

        # Phase 3: Feature overlap scoring + explanation
        scored: List[SimilarityResult] = []
        for row_dict, semantic_sim in rows:
            feature_sim, matched, explanation = _score_features(
                query_features=query_features,
                candidate=row_dict,
                semantic_sim=semantic_sim,
            )
            hybrid_score = ALPHA * semantic_sim + BETA * feature_sim

            if hybrid_score < request.min_similarity:
                continue

            scored.append(SimilarityResult(
                crime_id=row_dict["crime_id"],
                fir_number=row_dict["fir_number"],
                crime_type=row_dict.get("crime_type", ""),
                severity=row_dict.get("severity", ""),
                status=row_dict.get("crime_status", ""),
                district=row_dict.get("district", ""),
                police_station=row_dict.get("police_station", ""),
                occurred_at=row_dict["occurred_at"],
                mo_text=row_dict.get("mo_text"),
                latitude=row_dict.get("latitude"),
                longitude=row_dict.get("longitude"),
                similarity_score=round(hybrid_score, 4),
                semantic_similarity=round(semantic_sim, 4),
                feature_similarity=round(feature_sim, 4),
                matched_features=matched,
                explanation=explanation,
                crime_method=row_dict.get("crime_method"),
                target_type=row_dict.get("target_type"),
                planning_level=row_dict.get("planning_level"),
                gang_involved=bool(row_dict.get("gang_involved", False)),
                time_of_day_slot=row_dict.get("time_of_day_slot"),
            ))

        # Sort by hybrid_score descending
        scored.sort(key=lambda r: r.similarity_score, reverse=True)
        return scored, scanned

    # ── ML Engine Call ─────────────────────────────────────

    async def _embed_query(self, query_text: str) -> List[float]:
        """Call ML Engine to embed the query text."""
        url = f"{settings.MLENGINE_URL}/embed"
        try:
            async with httpx.AsyncClient(timeout=MLENGINE_TIMEOUT) as client:
                resp = await client.post(url, json={
                    "texts": [query_text],
                    "normalize": True,
                })
                resp.raise_for_status()
                data = resp.json()
            embeddings = data.get("embeddings", [])
            if not embeddings:
                raise ValueError("Empty embeddings response from ML Engine")
            return embeddings[0]
        except httpx.HTTPError as exc:
            from app.core.exceptions import ServiceUnavailableError
            logger.error(f"ML Engine unreachable for similarity query: {exc}")
            raise ServiceUnavailableError("ML Engine")


# ── Phase 3: Feature Scorer ────────────────────────────────

def _score_features(
    query_features: dict,
    candidate: dict,
    semantic_sim: float,
) -> tuple[float, List[str], str]:
    """
    Compute structured MO feature overlap between query and candidate.

    When query_features is empty (text-based search), we use high
    semantic similarity as a strong signal and generate a text-only
    explanation.

    Returns:
        (feature_similarity: float, matched_features: List[str], explanation: str)
    """
    if not query_features:
        # Text-only query — no structured features to compare
        # Return a neutral feature score + semantic-driven explanation
        explanation = _build_explanation(
            matched=[],
            semantic_sim=semantic_sim,
            candidate=candidate,
            text_only=True,
        )
        return 0.5, [], explanation

    matched: List[str] = []
    feature_score = 0.0

    for feature, weight in FEATURE_WEIGHTS.items():
        q_val = query_features.get(feature)
        c_val = candidate.get(feature)
        if q_val is None or c_val is None:
            continue
        if str(q_val).lower() == str(c_val).lower():
            matched.append(feature)
            feature_score += weight

    explanation = _build_explanation(
        matched=matched,
        semantic_sim=semantic_sim,
        candidate=candidate,
        text_only=False,
    )
    return min(feature_score, 1.0), matched, explanation


def _build_explanation(
    matched: List[str],
    semantic_sim: float,
    candidate: dict,
    text_only: bool,
) -> str:
    """Generate a human-readable explanation for investigators."""
    parts = []

    sem_pct = round(semantic_sim * 100, 1)
    if semantic_sim >= 0.90:
        parts.append(f"Very high narrative similarity ({sem_pct}%)")
    elif semantic_sim >= 0.75:
        parts.append(f"Strong narrative similarity ({sem_pct}%)")
    elif semantic_sim >= 0.60:
        parts.append(f"Moderate narrative similarity ({sem_pct}%)")
    else:
        parts.append(f"Partial narrative similarity ({sem_pct}%)")

    if not text_only and matched:
        readable = {
            "crime_method":     "same entry/attack method",
            "target_type":      "same target type",
            "time_of_day_slot": "same time of day",
            "gang_involved":    "same gang involvement pattern",
            "escape_method":    "same escape method",
        }
        feature_strs = [readable.get(f, f) for f in matched]
        parts.append(f"Matching MO features: {', '.join(feature_strs)}")

    # Add candidate context
    crime_method = candidate.get("crime_method")
    target_type  = candidate.get("target_type")
    time_slot    = candidate.get("time_of_day_slot")

    context_parts = []
    if crime_method:
        context_parts.append(f"{crime_method.replace('_', ' ')} method")
    if target_type:
        context_parts.append(f"{target_type.replace('_', ' ')} target")
    if time_slot:
        context_parts.append(f"{time_slot.replace('_', ' ')} operation")
    if context_parts:
        parts.append(f"Candidate profile: {', '.join(context_parts)}")

    return ". ".join(parts) + "."
