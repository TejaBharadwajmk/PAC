"""
PAC — Behavior Service

Coordinates PostgreSQL data aggregation, Neo4j network enrichment,
runs BehaviorEngine calculations, and manages database persistence for profiles.
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, timezone
from neo4j import AsyncSession as Neo4jSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.repositories.behavior_repo import BehaviorRepository
from app.models.behaviour import BehaviourProfile
from app.models.criminal import Criminal, CrimeCriminal
from app.models.crime import Crime
from app.models.crime_dna import CrimeDNA
from app.services.behavior_engine import BehaviorEngine
from app.graph_db import get_graph_session

logger = logging.getLogger(__name__)


class BehaviorService:
    """Orchestrates behaviour profile generation and queries."""

    def __init__(self, db_session, neo4j_session: Optional[Neo4jSession] = None) -> None:
        self.db = db_session
        self.neo4j = neo4j_session
        self.repo = BehaviorRepository(db_session)

    async def get_or_generate_profile(self, criminal_id: UUID) -> Optional[BehaviourProfile]:
        """Gets existing profile or generates a new one on the fly."""
        profile = await self.repo.get_by_criminal_id(criminal_id)
        if profile:
            # Let's check if it needs update (e.g., if there are new crimes not in generated_from_crimes)
            crimes_res = await self.db.execute(
                select(CrimeCriminal.crime_id).where(CrimeCriminal.criminal_id == criminal_id)
            )
            linked_crime_ids = [str(cid) for cid in crimes_res.scalars().all()]
            
            # If the set of crime IDs changed, regenerate the profile
            stored_crimes = profile.generated_from_crimes or []
            if set(linked_crime_ids) != set(stored_crimes):
                logger.info(f"Stale profile detected for criminal {criminal_id}. Regenerating...")
                return await self.generate_profile(criminal_id)
            return profile

        return await self.generate_profile(criminal_id)

    async def generate_profile(self, criminal_id: UUID) -> Optional[BehaviourProfile]:
        """Loads all data, runs the engine, and persists the BehaviourProfile."""
        logger.info(f"Generating behaviour profile for criminal: {criminal_id}")

        # 1. Fetch Criminal Profile
        criminal_res = await self.db.execute(
            select(Criminal).where(Criminal.id == criminal_id)
        )
        criminal = criminal_res.scalar_one_or_none()
        if not criminal:
            logger.error(f"Criminal not found in PostgreSQL: {criminal_id}")
            return None

        # 2. Fetch all linked Crimes and their DNA
        links_res = await self.db.execute(
            select(CrimeCriminal).where(CrimeCriminal.criminal_id == criminal_id)
        )
        links = links_res.scalars().all()
        crime_ids = [link.crime_id for link in links]

        crimes = []
        dnas = []
        if crime_ids:
            crimes_res = await self.db.execute(
                select(Crime).where(Crime.id.in_(crime_ids))
            )
            crimes = list(crimes_res.scalars().all())

            dnas_res = await self.db.execute(
                select(CrimeDNA).where(CrimeDNA.crime_id.in_(crime_ids))
            )
            dnas = list(dnas_res.scalars().all())

        # 3. Retrieve enrichment metrics from Neo4j
        network_metrics = {
            "co_offender_count": 0,
            "strongest_associate": None,
            "association_strength": 0.0,
            "gang_name": criminal.gang_name
        }

        if self.neo4j:
            try:
                network_metrics = await self._fetch_neo4j_network_metrics(criminal_id)
            except Exception as e:
                logger.warning(f"Failed to fetch Neo4j network metrics for behavior profile: {e}")

        # 4. Invoke Behavior Engine
        results = BehaviorEngine.analyze(criminal, crimes, dnas, network_metrics)

        # 5. Load or create BehaviourProfile model
        profile = await self.repo.get_by_criminal_id(criminal_id)
        if not profile:
            profile = BehaviourProfile(criminal_id=criminal_id)

        # Map stable fields
        profile.risk_score = results["scores"]["risk_score"]
        profile.risk_level = results["scores"]["risk_level"]
        profile.operating_radius_km = results["geo"]["operating_radius_km"]
        profile.behaviour_consistency_score = results["scores"]["behaviour_consistency_score"]
        profile.serial_offender_probability = results["scores"]["serial_offender_probability"]
        profile.behaviour_confidence_score = results["scores"]["behaviour_confidence_score"]
        profile.profile_version = "1.0"
        profile.generated_from_crimes = [str(cid) for cid in crime_ids]
        profile.last_updated = datetime.now(timezone.utc)
        profile.profile_summary = results["summary"]
        profile.detailed_metrics = results["detailed_metrics"]
        
        # Populate other new columns for easy querying
        geo_info = results["geo"]
        profile.preferred_police_station = geo_info["preferred_police_station"]
        profile.preferred_day_of_week = results["detailed_metrics"]["patterns"]["preferred_day_of_week"]
        profile.preferred_season_month = results["detailed_metrics"]["patterns"]["preferred_season_month"]
        profile.preferred_escape_method = results["detailed_metrics"]["patterns"]["preferred_escape_method"]
        profile.preferred_modus_operandi = results["detailed_metrics"]["patterns"]["modus_operandi_tags"]
        
        profile.gang_affiliation_score = results["scores"]["gang_affiliation_score"]
        profile.violence_score = results["scores"]["violence_score"]
        profile.repeat_offender_score = results["scores"]["repeat_offender_score"]
        profile.escalation_trend = results["detailed_metrics"]["timeline"]["escalation_trend"]

        # Save to database
        await self.repo.save(profile)
        await self.db.commit()
        
        # Trigger predictive risk update
        try:
            from app.services.prediction_service import PredictionService
            pred_svc = PredictionService(self.db, self.neo4j)
            await pred_svc.generate_criminal_prediction(criminal_id)
        except Exception as e:
            logger.error(f"Failed to auto-generate prediction forecast after behavior profile update: {e}")
        
        logger.info(f"Successfully generated profile for criminal {criminal_id}. Risk={profile.risk_level}")
        return profile

    async def rebuild_all_profiles(self) -> Dict[str, Any]:
        """Background job to rebuild behaviour profiles for all criminals in the system."""
        logger.info("Starting batch rebuild of all behaviour profiles...")
        
        # Get all criminal IDs
        res = await self.db.execute(select(Criminal.id))
        criminal_ids = res.scalars().all()
        
        count = 0
        for criminal_id in criminal_ids:
            try:
                await self.generate_profile(criminal_id)
                count += 1
            except Exception as e:
                logger.error(f"Error rebuilding profile for criminal {criminal_id}: {e}", exc_info=True)
                
        return {
            "success": True,
            "total_rebuilt": count
        }

    async def _fetch_neo4j_network_metrics(self, criminal_id: UUID) -> Dict[str, Any]:
        """Direct Cypher queries to aggregate network metrics from Neo4j."""
        c_id_str = str(criminal_id)
        
        # Query 1: Find count of co-offenders and strongest associate
        query = """
        MATCH (c:Criminal {id: $id})
        OPTIONAL MATCH (c)-[rel:CRIMINAL_ASSOCIATED_WITH_CRIMINAL]-(assoc:Criminal)
        WITH c, count(assoc) AS co_offenders, assoc, rel
        ORDER BY rel.association_strength DESC
        WITH c, co_offenders, collect({name: assoc.name, strength: rel.association_strength}) AS associates
        RETURN co_offenders, 
               CASE WHEN size(associates) > 0 THEN associates[0].name ELSE null END AS strongest_associate,
               CASE WHEN size(associates) > 0 THEN associates[0].strength ELSE 0.0 END AS association_strength
        """
        result = await self.neo4j.run(query, {"id": c_id_str})
        record = await result.single()
        
        # Query 2: Get gang name membership if any
        gang_query = """
        MATCH (c:Criminal {id: $id})-[:MEMBER_OF_GANG]->(g:Gang)
        RETURN g.name AS gang_name
        """
        gang_result = await self.neo4j.run(gang_query, {"id": c_id_str})
        gang_record = await gang_result.single()
        
        gang_name = gang_record["gang_name"] if gang_record else None
        
        if record:
            return {
                "co_offender_count": record["co_offenders"] or 0,
                "strongest_associate": record["strongest_associate"],
                "association_strength": float(record["association_strength"] or 0.0),
                "gang_name": gang_name
            }
            
        return {
            "co_offender_count": 0,
            "strongest_associate": None,
            "association_strength": 0.0,
            "gang_name": gang_name
        }
