"""
PAC — Retriever Service

Calls only the PAC intelligence modules selected by the Tool Router.
Each handler method returns a structured dict; the service aggregates
them into a single raw_context dict for the Evidence Ranker.

Retrieval is scoped:
  - No module is called unless it appears in the Tool Router's list.
  - Failures are logged and skipped; the pipeline continues with
    available data so the assistant always returns a useful response.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class RetrieverService:
    """Orchestrates selective retrieval from PAC intelligence modules."""

    def __init__(
        self,
        db: AsyncSession,
        neo4j_session: Optional[Any] = None,
    ) -> None:
        self.db = db
        self.neo4j = neo4j_session

    async def retrieve(
        self,
        modules: List[str],
        entity_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Retrieve data from the specified modules only.

        Args:
            modules:        Ordered list of module keys from ToolRouter.
            entity_context: Resolved entities from the conversation session
                            (criminal_id, crime_id, district, gang_name, query_text).

        Returns:
            raw_context dict with one key per successfully retrieved module.
        """
        raw_context: Dict[str, Any] = {}

        for module in modules:
            try:
                handler = getattr(self, f"_retrieve_{module}", None)
                if handler is None:
                    logger.warning(f"No retriever handler found for module: {module}")
                    continue
                data = await handler(entity_context)
                if data:
                    raw_context[module] = data
                    logger.debug(f"Retrieved data from module '{module}': {len(str(data))} chars")
            except Exception as exc:
                logger.warning(
                    f"Retrieval failed for module '{module}': {exc}. Continuing without it."
                )

        return raw_context

    # ── Module Handlers ────────────────────────────────────────────────────────

    async def _retrieve_dna(self, ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retrieve Crime DNA record for a specific crime."""
        crime_id = ctx.get("crime_id")
        if not crime_id:
            return None

        from app.repositories.dna_repo import DNARepository
        repo = DNARepository(self.db)
        dna = await repo.get_by_crime_id(UUID(str(crime_id)))
        if not dna:
            return None

        return {
            "crime_id": str(dna.crime_id),
            "status": dna.status,
            "crime_method": dna.crime_method,
            "target_type": dna.target_type,
            "escape_method": dna.escape_method,
            "planning_level": dna.planning_level,
            "gang_involved": dna.gang_involved,
            "time_of_day_slot": dna.time_of_day_slot,
            "mo_text": dna.mo_text,
            "mo_tags": dna.mo_tags,
        }

    async def _retrieve_similarity(self, ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retrieve similar crimes using the Hybrid Similarity Service."""
        crime_id = ctx.get("crime_id")
        query_text = ctx.get("query_text")

        if not crime_id and not query_text:
            return None

        from app.services.similarity_service import SimilarityService
        from app.schemas.dna import SimilaritySearchRequest

        svc = SimilarityService(self.db)

        if crime_id:
            response = await svc.search_by_crime_id(
                crime_id=UUID(str(crime_id)),
                limit=10,
                min_similarity=0.5,
                district=ctx.get("district"),
            )
        else:
            request = SimilaritySearchRequest(
                query_text=query_text,
                limit=10,
                min_similarity=0.5,
                district=ctx.get("district"),
            )
            response = await svc.search_by_text(request)

        return {
            "total_candidates": response.total_candidates_scanned,
            "results": [
                {
                    "crime_id": str(r.crime_id),
                    "fir_number": r.fir_number,
                    "crime_type": r.crime_type,
                    "district": r.district,
                    "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None,
                    "similarity_score": r.similarity_score,
                    "explanation": r.explanation,
                    "mo_text": r.mo_text,
                }
                for r in response.results
            ],
        }

    async def _retrieve_behaviour(self, ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retrieve Behaviour Profile for a criminal."""
        criminal_id = ctx.get("criminal_id")
        if not criminal_id:
            return None

        from app.services.behavior_service import BehaviorService
        svc = BehaviorService(self.db, self.neo4j)
        profile = await svc.get_or_generate_profile(UUID(str(criminal_id)))
        if not profile:
            return None

        dm = profile.detailed_metrics or {}
        return {
            "criminal_id": str(profile.criminal_id),
            "risk_level": profile.risk_level,
            "risk_score": float(profile.risk_score or 0),
            "profile_summary": profile.profile_summary,
            "escalation_trend": profile.escalation_trend,
            "violence_score": float(profile.violence_score or 0),
            "gang_affiliation_score": float(profile.gang_affiliation_score or 0),
            "operating_radius_km": float(profile.operating_radius_km or 0),
            "preferred_district": dm.get("geo", {}).get("preferred_district", ""),
            "preferred_time_slot": dm.get("patterns", {}).get("preferred_time_slot", ""),
            "primary_crime_type": dm.get("patterns", {}).get("primary_crime_type", ""),
            "evidence": dm.get("evidence", []),
            "recommendations": dm.get("recommendations", []),
            "scores": dm.get("scores", {}),
            "patterns": dm.get("patterns", {}),
        }

    async def _retrieve_prediction(self, ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retrieve Prediction Profile(s) relevant to the request context."""
        from app.services.prediction_service import PredictionService
        from app.repositories.prediction_repo import PredictionRepository

        svc = PredictionService(self.db, self.neo4j)
        repo = PredictionRepository(self.db)
        results: Dict[str, Any] = {}

        # Criminal risk
        criminal_id = ctx.get("criminal_id")
        if criminal_id:
            pred = await svc.get_or_generate_criminal_prediction(UUID(str(criminal_id)))
            if pred:
                results["criminal_risk"] = {
                    "risk_level": pred.risk_level,
                    "prediction_score": float(pred.prediction_score or 0),
                    "confidence": float(pred.confidence or 0),
                    "reason_code": pred.prediction_reason_code,
                    "evidence": pred.evidence or [],
                    "recommendations": pred.recommendations or [],
                    "score_breakdown": pred.score_breakdown or {},
                }

        # District risk
        district = ctx.get("district")
        if district:
            dist_pred = await repo.get_by_entity("district", district)
            if not dist_pred:
                dist_pred = await svc.generate_district_prediction(district)
            if dist_pred:
                results["district_risk"] = {
                    "district": district,
                    "risk_level": dist_pred.risk_level,
                    "score": float(dist_pred.prediction_score or 0),
                    "evidence": dist_pred.evidence or [],
                    "recommendations": dist_pred.recommendations or [],
                }

        # Gang threat
        gang_name = ctx.get("gang_name")
        if gang_name:
            gang_pred = await repo.get_by_entity("gang", gang_name)
            if not gang_pred:
                gang_pred = await svc.generate_gang_prediction(gang_name)
            if gang_pred:
                results["gang_threat"] = {
                    "gang_name": gang_name,
                    "threat_level": gang_pred.risk_level,
                    "score": float(gang_pred.prediction_score or 0),
                    "evidence": gang_pred.evidence or [],
                    "recommendations": gang_pred.recommendations or [],
                }

        return results if results else None

    async def _retrieve_graph(self, ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retrieve Neo4j criminal network data."""
        if not self.neo4j:
            return None

        criminal_id = ctx.get("criminal_id")
        gang_name = ctx.get("gang_name")
        results: Dict[str, Any] = {}

        if criminal_id:
            from app.repositories.graph_repo import GraphRepository
            repo = GraphRepository(self.neo4j)
            nodes, relationships = await repo.get_criminal_network(str(criminal_id))

            # Extract criminal associates from graph nodes
            associates = []
            for node in nodes:
                if (
                    node.get("label") == "Criminal"
                    and node.get("id") != str(criminal_id)
                ):
                    props = node.get("properties", {})
                    # Find relationship strength from relationships
                    strength = 0.0
                    times_seen = 0
                    for rel in relationships:
                        if rel.get("type") == "CRIMINAL_ASSOCIATED_WITH_CRIMINAL":
                            rel_props = rel.get("properties", {})
                            if rel.get("source") == str(criminal_id) or rel.get("target") == str(criminal_id):
                                strength = float(rel_props.get("association_strength", 0.0))
                                times_seen = int(rel_props.get("times_seen_together", 0))
                    associates.append({
                        "criminal_id": node.get("id"),
                        "name": props.get("name", "Unknown"),
                        "association_strength": strength,
                        "times_seen_together": times_seen,
                        "risk_score": props.get("risk_score", 0.0),
                    })

            results["criminal_network"] = {
                "associates": sorted(associates, key=lambda x: x["association_strength"], reverse=True)[:8],
                "total_nodes": len(nodes),
                "total_relationships": len(relationships),
                "crimes": [
                    node for node in nodes if node.get("label") == "Crime"
                ][:5],
            }

        if gang_name:
            from app.repositories.graph_repo import GraphRepository
            repo = GraphRepository(self.neo4j)
            gang_members = await repo.get_gang_members(gang_name)
            if gang_members:
                results["gang_members"] = gang_members

        return results if results else None

    async def _retrieve_geo(self, ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retrieve Geo Intelligence data — hotspots and statistics."""
        from app.services.geo_service import GeoService

        svc = GeoService(self.db)
        district = ctx.get("district")

        try:
            hotspots = await svc.get_hotspots(
                eps=1000.0,
                min_samples=3,
                district=district,
            )
            return {
                "hotspots": [
                    {
                        "cluster_id": h.cluster_id,
                        "center_latitude": h.center_latitude,
                        "center_longitude": h.center_longitude,
                        "crime_count": h.crime_count,
                        "dominant_crime_type": h.dominant_crime_type,
                        "peak_time": h.peak_time,
                        "hotspot_trend": h.hotspot_trend,
                        "risk_level": h.risk_level,
                        "confidence_score": h.confidence_score,
                        "suggested_patrol_window": h.suggested_patrol_window,
                        "recommendation": h.recommendation,
                    }
                    for h in hotspots[:10]  # cap at 10 for context budget
                ],
                "total_hotspots": len(hotspots),
                "district_filter": district,
            }
        except Exception as exc:
            logger.warning(f"Geo retrieval failed: {exc}")
            return None
