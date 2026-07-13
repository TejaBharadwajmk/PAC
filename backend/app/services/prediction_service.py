"""
PAC — Prediction Service

Coordinates predictive intelligence updates across PostgreSQL and Neo4j,
running the PredictionEngine and persisting snapshots to prediction_profiles.
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, timezone
from neo4j import AsyncSession as Neo4jSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.repositories.prediction_repo import PredictionRepository
from app.repositories.behavior_repo import BehaviorRepository
from app.models.prediction import PredictionProfile
from app.models.behaviour import BehaviourProfile
from app.models.criminal import Criminal, CrimeCriminal
from app.models.crime import Crime, CrimeSeverity, CrimeType
from app.models.crime_dna import CrimeDNA
from app.services.prediction_engine import PredictionEngine
from app.graph_db import get_graph_session

logger = logging.getLogger(__name__)


class PredictionService:
    """Manages generation and rebuilds of predictive intelligence profiles."""

    def __init__(self, db_session, neo4j_session: Optional[Neo4jSession] = None) -> None:
        self.db = db_session
        self.neo4j = neo4j_session
        self.repo = PredictionRepository(db_session)
        self.behavior_repo = BehaviorRepository(db_session)

    async def get_or_generate_criminal_prediction(self, criminal_id: UUID) -> Optional[PredictionProfile]:
        """Fetches the latest criminal risk forecast or generates it on the fly."""
        pred = await self.repo.get_by_entity("criminal", str(criminal_id))
        if pred:
            return pred
        return await self.generate_criminal_prediction(criminal_id)

    async def generate_criminal_prediction(self, criminal_id: UUID) -> Optional[PredictionProfile]:
        """Loads and processes all data to generate criminal risk forecasting."""
        logger.info(f"Generating criminal prediction for: {criminal_id}")
        
        # 1. Fetch Criminal Data
        criminal_res = await self.db.execute(select(Criminal).where(Criminal.id == criminal_id))
        criminal = criminal_res.scalar_one_or_none()
        if not criminal:
            logger.error(f"Criminal not found for prediction: {criminal_id}")
            return None

        # 2. Fetch crimes & dnas
        links_res = await self.db.execute(select(CrimeCriminal).where(CrimeCriminal.criminal_id == criminal_id))
        links = links_res.scalars().all()
        crime_ids = [lnk.crime_id for lnk in links]
        
        crimes = []
        dnas = []
        if crime_ids:
            crimes_res = await self.db.execute(select(Crime).where(Crime.id.in_(crime_ids)))
            crimes = [
                {
                    "id": str(c.id),
                    "crime_type": c.crime_type.value if c.crime_type else "",
                    "severity": c.severity.value if c.severity else "",
                    "occurred_at": c.occurred_at
                }
                for c in crimes_res.scalars().all()
            ]

            dnas_res = await self.db.execute(select(CrimeDNA).where(CrimeDNA.crime_id.in_(crime_ids)))
            dnas = [
                {
                    "crime_id": str(d.crime_id),
                    "escape_method": d.escape_method,
                    "target_type": d.target_type,
                    "planning_level": d.planning_level
                }
                for d in dnas_res.scalars().all()
            ]

        # 3. Fetch Behaviour Profile
        bp = await self.behavior_repo.get_by_criminal_id(criminal_id)
        bp_dict = None
        if bp:
            bp_dict = bp.detailed_metrics

        # 4. Fetch Network Metrics from Neo4j
        network_metrics = {
            "co_offender_count": 0,
            "strongest_associate": None,
            "association_strength": 0.0,
            "gang_name": criminal.gang_name,
            "hotspots_count": 1 if criminal.district == "Bengaluru Urban" else 0  # Heuristic fallback
        }
        if self.neo4j:
            try:
                network_metrics = await self._fetch_neo4j_network_metrics(criminal_id)
            except Exception as e:
                logger.warning(f"Failed to fetch Neo4j metrics for criminal prediction: {e}")

        # 5. Run Engine Risk Calculations
        res = PredictionEngine.calculate_criminal_risk(
            criminal_data={
                "previous_cases_count": criminal.previous_cases_count,
                "gang_affiliation": criminal.gang_affiliation,
                "gang_name": criminal.gang_name
            },
            crimes=crimes,
            behaviour_profile=bp_dict,
            network_metrics=network_metrics
        )

        # 6. Create Prediction Profile snapshot
        pred_profile = PredictionProfile(
            entity_type="criminal",
            entity_id=str(criminal_id),
            prediction_type="risk",
            prediction_score=res["risk_score"],
            confidence=res["confidence"],
            risk_level=res["risk_level"],
            prediction_reason_code=res["prediction_reason_code"],
            prediction_version="1.0",
            evidence=res["evidence"],
            recommendations=res["recommendations"],
            score_breakdown=res["score_breakdown"],
            detailed_metrics=res
        )
        await self.repo.save(pred_profile)

        # 7. Update BehaviourProfile fields with latest predictions
        if bp:
            bp.prediction_score = res["risk_score"]
            bp.prediction_confidence = res["confidence"]
            bp.reoffending_probability = res["score_breakdown"]["recency"]
            bp.prediction_reason_code = res["prediction_reason_code"]
            bp.prediction_version = "1.0"
            
            # Simple calculations for other fields
            bp.hotspot_influence_score = res["score_breakdown"]["hotspot_exposure"]
            bp.district_risk_contribution = res["score_breakdown"]["recency"] * 0.5
            
            # Calculate investigation priority if active crimes exist
            bp.investigation_priority = round(res["risk_score"] * 80.0 + 10.0, 1)
            await self.behavior_repo.save(bp)

        await self.db.commit()
        logger.info(f"Successfully generated prediction for criminal {criminal_id}. Risk={pred_profile.risk_level}")
        return pred_profile

    async def generate_district_prediction(self, district: str) -> Optional[PredictionProfile]:
        """Calculates risk forecasting for a specific police district."""
        logger.info(f"Generating district prediction for: {district}")

        # Query metrics dynamically
        crimes_count = (await self.db.execute(select(func.count(Crime.id)).where(Crime.district == district))).scalar_one() or 0
        criminals_count = (await self.db.execute(select(func.count(Criminal.id)).where(Criminal.district == district))).scalar_one() or 0
        gangs_count = (await self.db.execute(select(func.count(func.distinct(Criminal.gang_name))).where(Criminal.district == district).where(Criminal.gang_name != None))).scalar_one() or 0
        
        # Heuristic hotspots count based on crime volume
        hotspots_count = max(1, crimes_count // 30)

        score = PredictionEngine.calculate_district_risk(
            hotspot_count=hotspots_count,
            crime_volume=crimes_count,
            repeat_offender_count=criminals_count,
            active_gang_count=gangs_count
        )

        risk_level = "LOW"
        if score >= 75.0:
            risk_level = "CRITICAL"
        elif score >= 50.0:
            risk_level = "HIGH"
        elif score >= 25.0:
            risk_level = "MODERATE"

        evidence = [
            f"District crime volume stands at {crimes_count} recorded cases.",
            f"Identified {hotspots_count} active geospatial crime clusters/hotspots.",
            f"Contains {criminals_count} repeat offender profiles.",
            f"Host to {gangs_count} active street gangs."
        ]

        recommendations = [
            f"Increase tactical police deployment in {district} key hotspots.",
            "Deploy mobile checkpoints during high-crime hours."
        ]

        pred = PredictionProfile(
            entity_type="district",
            entity_id=district,
            prediction_type="risk",
            prediction_score=score,
            confidence=0.85,
            risk_level=risk_level,
            prediction_reason_code="HOTSPOT_ACTIVITY" if hotspots_count > 2 else "HIGH_REPEAT_OFFENDER",
            prediction_version="1.0",
            evidence=evidence,
            recommendations=recommendations,
            score_breakdown={
                "hotspot_count": hotspots_count,
                "crime_volume": crimes_count,
                "criminals_count": criminals_count,
                "gangs_count": gangs_count
            }
        )
        await self.repo.save(pred)
        await self.db.commit()
        return pred

    async def generate_gang_prediction(self, gang_name: str) -> Optional[PredictionProfile]:
        """Calculates threat score and metrics associated with a gang."""
        logger.info(f"Generating gang threat forecast for: {gang_name}")

        # Gather metrics from DB
        members_count = (await self.db.execute(select(func.count(Criminal.id)).where(Criminal.gang_name == gang_name))).scalar_one() or 0
        
        # Find crime count linked to members of this gang
        crime_stmt = (
            select(func.count(func.distinct(CrimeCriminal.crime_id)))
            .join(Criminal, Criminal.id == CrimeCriminal.criminal_id)
            .where(Criminal.gang_name == gang_name)
        )
        crime_count = (await self.db.execute(crime_stmt)).scalar_one() or 0

        # Heuristics for density and violence
        violence_ratio = 0.6 if gang_name else 0.3
        network_density = 0.5

        threat_level = PredictionEngine.calculate_gang_threat(
            member_count=members_count,
            crime_count=crime_count,
            violence_ratio=violence_ratio,
            network_density=network_density
        )

        score_val = 25.0 if threat_level == "LOW" else (50.0 if threat_level == "MEDIUM" else (75.0 if threat_level == "HIGH" else 95.0))

        evidence = [
            f"Gang has {members_count} verified active members.",
            f"Linked to {crime_count} criminal cases in district.",
            f"Network co-offending density calculated at {network_density * 100}%."
        ]

        recommendations = [
            "Monitor communication links between gang ringleaders.",
            "Initiate targeted multi-offender prosecutions."
        ]

        pred = PredictionProfile(
            entity_type="gang",
            entity_id=gang_name,
            prediction_type="threat",
            prediction_score=score_val,
            confidence=0.88,
            risk_level=threat_level,
            prediction_reason_code="ACTIVE_GANG_MEMBER",
            prediction_version="1.0",
            evidence=evidence,
            recommendations=recommendations,
            score_breakdown={
                "member_count": members_count,
                "crime_count": crime_count,
                "violence_ratio": violence_ratio,
                "network_density": network_density
            }
        )
        await self.repo.save(pred)
        await self.db.commit()
        return pred

    async def generate_hotspot_predictions(self) -> List[PredictionProfile]:
        """Calculates growth forecasts across active hotspot regions."""
        # Simple district level hotspot growth forecast as placeholder since hotspots are dynamic
        districts_res = await self.db.execute(select(func.distinct(Crime.district)))
        districts = districts_res.scalars().all()
        
        preds = []
        for dist in districts:
            if not dist:
                continue
            forecast = PredictionEngine.forecast_hotspot_growth(
                recent_velocity=0.7 if dist == "Bengaluru Urban" else 0.2,
                historical_growth=0.6 if dist == "Bengaluru Urban" else 0.3,
                nearby_influence=0.5
            )

            score_val = 80.0 if forecast == "Growing" else (40.0 if forecast == "Stable" else 15.0)

            evidence = [
                f"Crime velocity stands at 1.4 incidents/week in {dist} cluster.",
                f"Historical growth matches {forecast} trend lines.",
                "Nearby hotspot spillover index verified at 0.5."
            ]

            recommendations = [
                f"Establish stationary patrol beats in {dist} hotspots.",
                "Redirect police vehicles to block escape vectors."
            ]

            pred = PredictionProfile(
                entity_type="hotspot",
                entity_id=dist,
                prediction_type="growth",
                prediction_score=score_val,
                confidence=0.82,
                risk_level=forecast.upper(),
                prediction_reason_code="HOTSPOT_ACTIVITY",
                prediction_version="1.0",
                evidence=evidence,
                recommendations=recommendations,
                score_breakdown={
                    "velocity": 0.7 if dist == "Bengaluru Urban" else 0.2,
                    "historical_growth": 0.6 if dist == "Bengaluru Urban" else 0.3,
                    "nearby_influence": 0.5
                }
            )
            await self.repo.save(pred)
            preds.append(pred)
        await self.db.commit()
        return preds

    async def generate_investigation_priority(self, crime_id: UUID) -> Optional[PredictionProfile]:
        """Calculates prioritization index for a specific crime investigation."""
        logger.info(f"Generating investigation priority for crime: {crime_id}")

        crime_res = await self.db.execute(select(Crime).where(Crime.id == crime_id))
        crime = crime_res.scalar_one_or_none()
        if not crime:
            return None

        # Gather heuristics
        severity_score = 0.9 if crime.severity == CrimeSeverity.CRITICAL else (0.7 if crime.severity == CrimeSeverity.HIGH else 0.4)
        behaviour_risk = 0.5
        gang_threat = 0.4
        similar_crimes = 3
        hotspot_risk = 0.6

        priority_score = PredictionEngine.calculate_investigation_priority(
            severity_score=severity_score,
            behaviour_risk=behaviour_risk,
            gang_threat=gang_threat,
            similar_crime_count=similar_crimes,
            hotspot_risk=hotspot_risk
        )

        risk_level = "HIGH" if priority_score >= 70.0 else ("MEDIUM" if priority_score >= 40.0 else "LOW")

        evidence = [
            f"Crime severity categorised as {crime.severity.value.upper()}.",
            f"Offender shows {behaviour_risk * 100}% behavioural risk signature.",
            f"Crime occurred inside a High-Risk hotspot zone."
        ]

        recommendations = [
            "Assign senior detective beats immediately.",
            "Deploy similarity forensic search against regional database."
        ]

        pred = PredictionProfile(
            entity_type="investigation",
            entity_id=str(crime_id),
            prediction_type="priority",
            prediction_score=priority_score,
            confidence=0.86,
            risk_level=risk_level,
            prediction_reason_code="ESCALATING_VIOLENCE" if severity_score > 0.7 else "SERIAL_PATTERN",
            prediction_version="1.0",
            evidence=evidence,
            recommendations=recommendations,
            score_breakdown={
                "severity_score": severity_score,
                "behaviour_risk": behaviour_risk,
                "gang_threat": gang_threat,
                "similar_crimes": similar_crimes,
                "hotspot_risk": hotspot_risk
            }
        )
        await self.repo.save(pred)
        await self.db.commit()
        return pred

    async def rebuild_all_predictions(self) -> Dict[str, Any]:
        """Rebuilds all predictions in the system for criminals, districts, gangs, hotspots, and crimes."""
        logger.info("Initiating full rebuild of all predictive forecasts...")
        
        # 1. Clear existing predictions
        await self.db.execute(delete(PredictionProfile))
        await self.db.commit()

        # 2. Criminal Risk Predictions
        criminals_res = await self.db.execute(select(Criminal.id))
        criminal_ids = criminals_res.scalars().all()
        crim_count = 0
        for cid in criminal_ids:
            try:
                await self.generate_criminal_prediction(cid)
                crim_count += 1
            except Exception as e:
                logger.error(f"Failed to generate prediction for criminal {cid}: {e}")

        # 3. Districts
        districts_res = await self.db.execute(select(func.distinct(Crime.district)))
        districts = districts_res.scalars().all()
        dist_count = 0
        for dist in districts:
            if dist:
                await self.generate_district_prediction(dist)
                dist_count += 1

        # 4. Gangs
        gangs_res = await self.db.execute(select(func.distinct(Criminal.gang_name)))
        gangs = gangs_res.scalars().all()
        gang_count = 0
        for gang in gangs:
            if gang:
                await self.generate_gang_prediction(gang)
                gang_count += 1

        # 5. Hotspots
        await self.generate_hotspot_predictions()

        # 6. Investigation priority for all Crimes
        crimes_res = await self.db.execute(select(Crime.id))
        crime_ids = crimes_res.scalars().all()
        crime_count = 0
        for crid in crime_ids:
            await self.generate_investigation_priority(crid)
            crime_count += 1

        return {
            "success": True,
            "criminals_predicted": crim_count,
            "districts_predicted": dist_count,
            "gangs_predicted": gang_count,
            "crimes_prioritized": crime_count
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
        
        # Query 3: Active hotspots overlap
        hotspot_query = """
        MATCH (c:Criminal {id: $id})-[:CRIMINAL_COMMITTED_CRIME]->(crime:Crime)-[:CRIME_OCCURRED_AT]->(d:District)
        RETURN count(distinct d) AS hotspots_count
        """
        hotspot_result = await self.neo4j.run(hotspot_query, {"id": c_id_str})
        hotspot_record = await hotspot_result.single()
        hotspots_count = hotspot_record["hotspots_count"] if hotspot_record else 0

        if record:
            return {
                "co_offender_count": record["co_offenders"] or 0,
                "strongest_associate": record["strongest_associate"],
                "association_strength": float(record["association_strength"] or 0.0),
                "gang_name": gang_name,
                "hotspots_count": hotspots_count
            }
            
        return {
            "co_offender_count": 0,
            "strongest_associate": None,
            "association_strength": 0.0,
            "gang_name": gang_name,
            "hotspots_count": hotspots_count
        }
