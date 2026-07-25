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
    SearchDebugInfo,
)
from app.services.mo_extractor import mo_extractor
from app.services.hybrid_rank_engine import RankingSignal, HybridRankEngine
from app.services.explainability_builder import ExplainabilityBuilder

logger = logging.getLogger(__name__)

def get_mo_feature_weights() -> dict:
    return {
        "crime_type":        settings.MO_CRIME_TYPE_WEIGHT,
        "crime_method":     settings.MO_CRIME_METHOD_WEIGHT,
        "weapon_used":      settings.MO_WEAPON_WEIGHT,
        "entry_method":     settings.MO_ENTRY_METHOD_WEIGHT,
        "target_type":      settings.MO_TARGET_WEIGHT,
        "escape_method":    settings.MO_ESCAPE_WEIGHT,
        "time_of_day_slot": settings.MO_TIME_WEIGHT,
        "gang_involved":    settings.MO_GANG_WEIGHT,
        "district":         settings.MO_DISTRICT_WEIGHT,
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
          2. Extract structured MO features using Synonym Engine
          3. Run hybrid search
          4. Return ranked results with explanations
        """
        # Embed the query text
        query_embedding = await self._embed_query(request.query_text)

        # Extract query features config-driven
        query_features, confidence, matched_keywords, unknown_tokens = mo_extractor.extract_query_features(request.query_text)

        results, scanned, debug_info = await self._hybrid_search(
            query_embedding=query_embedding,
            exclude_crime_id=None,
            request=request,
            query_text=request.query_text,
            query_features=query_features,
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
            debug=debug_info if request.include_debug else None,
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
            query_text="placeholder",          # not used in this mode
            limit=limit,
            min_similarity=min_similarity,
            district=district,
        )

        # Convert pgvector column to plain Python list
        raw_embedding = list(dna.embedding)

        # Fetch entry_method from crime_mo to prevent lazy-load exceptions in async ORM
        from app.models.crime import CrimeMO
        from sqlalchemy import select
        mo_res = await self.db.execute(
            select(CrimeMO.entry_method).where(CrimeMO.crime_id == crime_id)
        )
        entry_method = mo_res.scalar_one_or_none()

        # Build query features from source crime DNA record
        query_features = {
            "crime_type":        dna.crime_type,
            "crime_method":     dna.crime_method,
            "weapon_used":      dna.weapon_used,
            "entry_method":     entry_method,
            "target_type":      dna.target_type,
            "escape_method":    dna.escape_method,
            "time_of_day_slot": dna.time_of_day_slot,
            "gang_involved":    dna.gang_involved,
            "district":         dna.district,
        }

        results, scanned, _debug = await self._hybrid_search(
            query_embedding=raw_embedding,
            exclude_crime_id=crime_id,
            request=request,
            query_text=dna.mo_text_embedded,
            query_features=query_features,
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
        query_text: Optional[str] = None,
        query_features: Optional[dict] = None,
    ) -> tuple[List[SimilarityResult], int, Optional[SearchDebugInfo]]:
        """
        Run the full 3-phase hybrid search.

        Returns (ranked_results, total_candidates_scanned, debug_info).
        debug_info is populated from the first scored candidate (representative
        of all candidates — weights are uniform across the result set).
        """
        if query_features is None:
            query_features = {}

        # Phase 1 + 2: SQL pre-filter + pgvector ANN + FTS
        max_distance = 0.95
        rows = await self.repo.find_similar(

            query_embedding=query_embedding,
            query_text=query_text,
            exclude_crime_id=exclude_crime_id,
            limit=ANN_OVERFETCH,
            max_distance=max_distance,
            district_filter=request.district,
            crime_type_filter=request.crime_type.value if request.crime_type else None,
            time_slot_filter=request.time_of_day_slot,
        )

        scanned = len(rows)

        if not rows:
            return [], 0, None

        # Resolve weights: per-request overrides take precedence over settings
        semantic_w = request.semantic_weight if request.semantic_weight is not None else settings.HYBRID_SEMANTIC_WEIGHT
        fts_w      = request.fts_weight      if request.fts_weight      is not None else settings.HYBRID_FTS_WEIGHT
        mo_w       = request.mo_weight       if request.mo_weight       is not None else settings.HYBRID_MO_WEIGHT

        # Phase 3: Feature overlap scoring + explanation
        scored: List[SimilarityResult] = []
        last_fusion = None   # capture for debug block
        for row_dict, semantic_sim, fts_score in rows:
            mo_score, matched, missing = _score_features(
                query_features=query_features,
                candidate=row_dict,
            )

            # Signal-agnostic ranking signals list
            signals = [
                RankingSignal(
                    name="semantic",
                    value=semantic_sim,
                    weight=semantic_w,
                    active=True,
                ),
                RankingSignal(
                    name="fts",
                    value=min(fts_score, 1.0),
                    weight=fts_w,
                    active=bool(query_text and query_text.strip()),
                ),
                RankingSignal(
                    name="mo",
                    value=mo_score if mo_score is not None else 0.0,
                    weight=mo_w,
                    active=mo_score is not None,
                ),
            ]

            # Dynamic Rank Fusion via signal-agnostic Engine
            fusion = HybridRankEngine.fuse(signals)
            hybrid_score = fusion.score
            if last_fusion is None:
                last_fusion = fusion   # capture first result for debug block

            if hybrid_score < request.min_similarity:
                continue

            # Build exact matched terms
            if query_text and query_text.strip():
                matched_terms = _extract_matched_terms(query_text, row_dict)
            else:
                matched_terms = []

            # Build explainable narrative via decoupled Explainability Builder
            explanations_list, explanation_str = ExplainabilityBuilder.build(
                semantic_sim=semantic_sim,
                fts_score=min(fts_score, 1.0),
                mo_score=mo_score,
                matched_features=matched,
                missing_features=missing,
                matched_terms=matched_terms,
            )

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
                feature_similarity=round(mo_score if mo_score is not None else 0.0, 4),
                
                # Extended parameters for Phase 5 API contract
                final_score=round(hybrid_score, 4),
                semantic_score=round(semantic_sim, 4),
                fts_score=round(min(fts_score, 1.0), 4),
                mo_score=round(mo_score, 4) if mo_score is not None else None,
                matched_terms=matched_terms,
                explanations=explanations_list,
                
                matched_features=matched,
                missing_features=missing,
                explanation=explanation_str,
                crime_method=row_dict.get("crime_method"),
                target_type=row_dict.get("target_type"),
                planning_level=row_dict.get("planning_level"),
                gang_involved=bool(row_dict.get("gang_involved", False)),
                time_of_day_slot=row_dict.get("time_of_day_slot"),
            ))

        # Sort by hybrid_score descending
        scored.sort(key=lambda r: r.similarity_score, reverse=True)

        # Build debug info from captured fusion diagnostics
        debug_info: Optional[SearchDebugInfo] = None
        if last_fusion is not None:
            debug_info = SearchDebugInfo(
                active_signals=last_fusion.active_signals,
                normalized_weights=last_fusion.normalized_weights,
                configured_weights=last_fusion.configured_weights,
            )

        return scored, scanned, debug_info

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


def _extract_matched_terms(query_text: str, candidate: dict) -> List[str]:
    """Helper to trace exact query tokens matched inside candidate fields."""
    if not query_text:
        return []
    import re
    words = re.findall(r'\w+', query_text.lower())
    matched = []
    searchable_text = " ".join([
        str(candidate.get("fir_number", "")),
        str(candidate.get("description", "")),
        str(candidate.get("mo_text", "")),
        str(candidate.get("location_address", "")),
        str(candidate.get("police_station", "")),
        str(candidate.get("district", "")),
        str(candidate.get("weapon_used", "")),
        str(candidate.get("crime_method", "")),
        str(candidate.get("entry_method", "")),
        str(candidate.get("target_type", "")),
    ]).lower()
    for w in set(words):
        if len(w) > 2 and w in searchable_text:
            matched.append(w)
    return sorted(matched)


# ── Phase 3: Feature Scorer ────────────────────────────────

def _score_features(
    query_features: dict,
    candidate: dict,
) -> tuple[Optional[float], List[str], List[str]]:
    """
    Compute structured MO feature similarity (weighted overlap) between query and candidate.

    Returns:
        (mo_score: Optional[float], matched_features: List[str], missing_features: List[str])
    """
    # Exclude null values from query features
    active_query_features = {k: v for k, v in query_features.items() if v is not None}
    if not active_query_features:
        return None, [], []

    weights = get_mo_feature_weights()
    
    matched: List[str] = []
    missing: List[str] = []
    
    matched_weight = 0.0
    total_weight = 0.0
    
    for feature in weights.keys():
        q_val = active_query_features.get(feature)
        if q_val is None:
            continue
            
        total_weight += weights[feature]
        c_val = candidate.get(feature)
        
        # Handle boolean comparison
        if isinstance(q_val, bool) or isinstance(c_val, bool):
            match = bool(q_val) == bool(c_val)
        else:
            match = str(q_val).lower().strip() == str(c_val).lower().strip()
            
        if match:
            matched.append(feature)
            matched_weight += weights[feature]
        else:
            missing.append(feature)

    if total_weight == 0:
        return None, [], []
        
    mo_score = matched_weight / total_weight
    return round(mo_score, 4), matched, missing
