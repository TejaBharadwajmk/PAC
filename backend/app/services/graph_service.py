"""
PAC — Criminal Network Intelligence (Graph) Service
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from neo4j import AsyncSession as Neo4jSession

from app.database import AsyncSessionLocal
from app.graph_db import get_graph_session
from app.repositories.graph_repo import GraphRepository
from app.models.crime import Crime
from app.models.criminal import Criminal, CrimeCriminal
from app.models.victim import CrimeVictim
from app.models.behaviour import BehaviourProfile
from app.schemas.graph import GraphNetworkResponse, ShortestPathResponse, GraphStatisticsResponse

logger = logging.getLogger(__name__)


class GraphService:
    """Coordinates PostgreSQL data loading and Neo4j graph indexing/synchronization."""

    def __init__(self, db: AsyncSession, graph_db: Neo4jSession) -> None:
        self.db = db
        self.graph_db = graph_db
        self.repo = GraphRepository(graph_db)

    async def sync_crime(self, crime_id: UUID) -> None:
        """Loads a single crime from PostgreSQL and updates the Neo4j graph model."""
        stmt = select(Crime).options(
            selectinload(Crime.crime_dna),
            selectinload(Crime.victims).selectinload(CrimeVictim.victim)
        ).where(Crime.id == crime_id)
        res = await self.db.execute(stmt)
        crime = res.scalar_one_or_none()
        if not crime:
            logger.warning(f"Crime not found in PostgreSQL for graph sync: {crime_id}")
            return

        # 1. Format and sync crime node
        crime_data = self._format_crime(crime)
        await self.repo.sync_crime_nodes_batch([crime_data])

        # 2. Query and sync all links/offenders associated with this crime
        links_stmt = select(CrimeCriminal).where(CrimeCriminal.crime_id == crime_id)
        links_res = await self.db.execute(links_stmt)
        links = links_res.scalars().all()
        
        if links:
            links_data = [
                {
                    "crime_id": str(link.crime_id),
                    "criminal_id": str(link.criminal_id),
                    "role": link.role.value if link.role else "accused",
                    "is_arrested": link.is_arrested,
                }
                for link in links
            ]
            await self.repo.sync_crime_criminals_batch(links_data)
            
        await self.repo.update_gang_summaries()
        logger.info(f"Synchronized crime {crime_id} to Neo4j.")

    async def sync_criminal(self, criminal_id: UUID) -> None:
        """Loads a single criminal profile from PostgreSQL and updates Neo4j."""
        stmt = select(Criminal).options(
            selectinload(Criminal.behaviour_profile)
        ).where(Criminal.id == criminal_id)
        res = await self.db.execute(stmt)
        criminal = res.scalar_one_or_none()
        if not criminal:
            logger.warning(f"Criminal not found in PostgreSQL for graph sync: {criminal_id}")
            return

        # Get committed crimes for primary crime type computation
        links_stmt = select(CrimeCriminal).options(
            selectinload(CrimeCriminal.crime)
        ).where(CrimeCriminal.criminal_id == criminal_id)
        links_res = await self.db.execute(links_stmt)
        links = links_res.scalars().all()

        criminal_data = self._format_criminal(criminal, links)
        await self.repo.sync_criminal_nodes_batch([criminal_data])
        
        await self.repo.update_gang_summaries()
        logger.info(f"Synchronized criminal {criminal_id} to Neo4j.")

    async def rebuild_graph(self, batch_size: int = 500) -> Dict[str, Any]:
        """ Wipes Neo4j and fully repopulates the graph from PostgreSQL in optimized batches. """
        logger.warning("Initiating full Neo4j graph database rebuild...")
        
        # 1. Clear the graph
        await self.repo.clear_graph()

        # 2. Sync all Crimes in batches
        crime_offset = 0
        total_crimes = 0
        while True:
            stmt = select(Crime).options(
                selectinload(Crime.crime_dna),
                selectinload(Crime.victims).selectinload(CrimeVictim.victim)
            ).order_by(Crime.id).offset(crime_offset).limit(batch_size)
            
            res = await self.db.execute(stmt)
            crimes = res.scalars().all()
            if not crimes:
                break
            
            crimes_batch = [self._format_crime(c) for c in crimes]
            await self.repo.sync_crime_nodes_batch(crimes_batch)
            total_crimes += len(crimes)
            crime_offset += batch_size

        # 3. Sync all Criminals in batches
        criminal_offset = 0
        total_criminals = 0
        while True:
            stmt = select(Criminal).options(
                selectinload(Criminal.behaviour_profile)
            ).order_by(Criminal.id).offset(criminal_offset).limit(batch_size)
            
            res = await self.db.execute(stmt)
            criminals = res.scalars().all()
            if not criminals:
                break
            
            # Fetch co-offending links for all criminals in the batch to avoid N+1 queries
            criminal_ids = [c.id for c in criminals]
            links_stmt = select(CrimeCriminal).options(
                selectinload(CrimeCriminal.crime)
            ).where(CrimeCriminal.criminal_id.in_(criminal_ids))
            
            links_res = await self.db.execute(links_stmt)
            links = links_res.scalars().all()
            
            # Group links by criminal ID in memory
            links_map = {}
            for link in links:
                links_map.setdefault(link.criminal_id, []).append(link)

            criminals_batch = [self._format_criminal(c, links_map.get(c.id, [])) for c in criminals]
            await self.repo.sync_criminal_nodes_batch(criminals_batch)
            total_criminals += len(criminals)
            criminal_offset += batch_size

        # 4. Sync all committed links (CRIMINAL_COMMITTED_CRIME and co-offenders)
        link_offset = 0
        total_links = 0
        while True:
            links_stmt = select(CrimeCriminal).order_by(CrimeCriminal.id).offset(link_offset).limit(batch_size)
            links_res = await self.db.execute(links_stmt)
            links = links_res.scalars().all()
            if not links:
                break

            links_batch = [
                {
                    "crime_id": str(link.crime_id),
                    "criminal_id": str(link.criminal_id),
                    "role": link.role.value if link.role else "accused",
                    "is_arrested": link.is_arrested,
                }
                for link in links
            ]
            await self.repo.sync_crime_criminals_batch(links_batch)
            total_links += len(links)
            link_offset += batch_size

        # 5. Refresh Gang node counts and active districts
        await self.repo.update_gang_summaries()

        logger.info(f"Graph rebuild complete. Crimes: {total_crimes}, Criminals: {total_criminals}, Relationships: {total_links}")
        return {
            "crimes_synced": total_crimes,
            "criminals_synced": total_criminals,
            "relationships_synced": total_links,
        }

    async def get_criminal_network(self, criminal_id: UUID) -> GraphNetworkResponse:
        """Fetches the graph network surrounding a criminal."""
        nodes, rels = await self.repo.get_criminal_network(str(criminal_id))
        return GraphNetworkResponse(nodes=nodes, relationships=rels)

    async def get_shortest_path(self, criminal_id1: UUID, criminal_id2: UUID) -> ShortestPathResponse:
        """Calculates degrees of separation / shortest path between two criminals."""
        res = await self.repo.get_shortest_path(str(criminal_id1), str(criminal_id2))
        if not res:
            return ShortestPathResponse(nodes=[], relationships=[], distance=0, found=False)
        nodes, rels, distance = res
        return ShortestPathResponse(nodes=nodes, relationships=rels, distance=distance, found=True)

    async def get_gang_network(self, gang_name: str) -> GraphNetworkResponse:
        """Fetches the co-offending network associated with a specific gang."""
        nodes, rels = await self.repo.get_gang_network(gang_name)
        return GraphNetworkResponse(nodes=nodes, relationships=rels)

    async def get_statistics(self) -> GraphStatisticsResponse:
        """Fetches the total counts of nodes and relationships from Neo4j."""
        stats = await self.repo.get_graph_statistics()
        return GraphStatisticsResponse(
            node_counts=stats["node_counts"],
            relationship_counts=stats["relationship_counts"]
        )

    async def get_common_associates(self, criminal_id: UUID) -> List[Dict[str, Any]]:
        """Retrieves list of co-offending matches who share associates with the criminal."""
        return await self.repo.get_common_associates(str(criminal_id))

    # ── Formatting Helpers ─────────────────────────────────

    def _format_crime(self, crime: Crime) -> Dict[str, Any]:
        """Serializes a Crime database object into a clean dictionary for Neo4j import."""
        dna_status = None
        similarity_ready = False
        if crime.crime_dna:
            dna_status = crime.crime_dna.status.value
            similarity_ready = (dna_status == "completed" and crime.crime_dna.embedding is not None)

        return {
            "id": str(crime.id),
            "fir_number": crime.fir_number,
            "crime_type": crime.crime_type.value,
            "severity": crime.severity.value,
            "occurred_at": crime.occurred_at.isoformat(),
            "dna_status": dna_status,
            "similarity_ready": similarity_ready,
            "district": crime.district,
            "police_station": crime.police_station,
            "victims": [
                {
                    "id": str(cv.victim.id),
                    "name": cv.victim.name,
                    "gender": cv.victim.gender,
                    "age": cv.victim.age,
                }
                for cv in crime.victims if cv.victim
            ]
        }

    def _format_criminal(self, criminal: Criminal, links: List[CrimeCriminal]) -> Dict[str, Any]:
        """Formats a Criminal DB profile and aggregates crime records into a Neo4j record."""
        # 1. Compute Primary Crime Type
        counts = {}
        for link in links:
            if link.crime:
                c_type = link.crime.crime_type.value
                counts[c_type] = counts.get(c_type, 0) + 1
        primary_crime_type = max(counts, key=counts.get) if counts else "unknown"

        # 2. Extract or Compute Risk Score
        risk_score = 0.0
        if criminal.behaviour_profile:
            risk_score = criminal.behaviour_profile.risk_score
        else:
            # Fallback heuristic based on recidivism counts
            risk_score = min(1.0, 0.8 if criminal.is_repeat_offender else (0.1 * criminal.previous_cases_count))
            risk_score = round(risk_score, 2)

        # 3. Known aliases
        known_aliases = list(criminal.aliases) if criminal.aliases else []

        return {
            "id": str(criminal.id),
            "name": criminal.name,
            "is_repeat_offender": criminal.is_repeat_offender,
            "risk_score": float(risk_score),
            "primary_crime_type": primary_crime_type,
            "known_aliases": known_aliases,
            "district": criminal.district,
            "gang_name": criminal.gang_name,
        }


async def sync_crime_to_graph(crime_id: UUID) -> None:
    """Helper background task function to synchronize a single crime to Neo4j."""
    async with AsyncSessionLocal() as session:
        async with get_graph_session() as g_session:
            service = GraphService(session, g_session)
            await service.sync_crime(crime_id)
            
            # Fetch all criminals linked to this crime
            try:
                links_res = await session.execute(
                    select(CrimeCriminal.criminal_id).where(CrimeCriminal.crime_id == crime_id)
                )
                criminal_ids = links_res.scalars().all()
                if criminal_ids:
                    from app.services.behavior_service import BehaviorService
                    from app.services.prediction_service import PredictionService
                    behavior_service = BehaviorService(session, g_session)
                    pred_svc = PredictionService(session, g_session)
                    for criminal_id in criminal_ids:
                        await behavior_service.generate_profile(criminal_id)
                        
                        # Trigger gang threat update if gang member
                        res = await session.execute(
                            select(Criminal.gang_name).where(Criminal.id == criminal_id)
                        )
                        gang_name = res.scalar_one_or_none()
                        if gang_name:
                            await pred_svc.generate_gang_prediction(gang_name)
            except Exception as e:
                logger.error(f"Failed to auto-regenerate behavior profiles after crime graph sync: {e}")


async def sync_criminal_to_graph(criminal_id: UUID) -> None:
    """Helper background task function to synchronize a single criminal to Neo4j."""
    async with AsyncSessionLocal() as session:
        async with get_graph_session() as g_session:
            service = GraphService(session, g_session)
            await service.sync_criminal(criminal_id)
            
            # Regenerate this criminal's behavior profile
            try:
                from app.services.behavior_service import BehaviorService
                from app.services.prediction_service import PredictionService
                behavior_service = BehaviorService(session, g_session)
                await behavior_service.generate_profile(criminal_id)
                
                # Trigger gang threat update if gang member
                res = await session.execute(
                    select(Criminal.gang_name).where(Criminal.id == criminal_id)
                )
                gang_name = res.scalar_one_or_none()
                if gang_name:
                    pred_svc = PredictionService(session, g_session)
                    await pred_svc.generate_gang_prediction(gang_name)
            except Exception as e:
                logger.error(f"Failed to auto-regenerate behavior profile after criminal graph sync: {e}")
