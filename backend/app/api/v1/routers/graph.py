"""
PAC — Criminal Network Intelligence (Graph) Router
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status, HTTPException
from pydantic import BaseModel, Field
from neo4j import AsyncSession

from app.dependencies import DbSession, CurrentUser
from app.graph_db import get_neo4j_session
from app.services.graph_service import GraphService
from app.schemas.graph import (
    GraphNetworkResponse,
    ShortestPathResponse,
    GraphStatisticsResponse,
    GraphSyncResponse,
)
from app.schemas.common import MessageResponse

router = APIRouter()


class SyncRequest(BaseModel):
    """Payload to trigger partial synchronization for specific crimes or criminals."""
    crime_ids: Optional[List[UUID]] = Field(default=None, description="List of crime IDs to sync")
    criminal_ids: Optional[List[UUID]] = Field(default=None, description="List of criminal IDs to sync")


@router.post(
    "/sync",
    response_model=GraphSyncResponse,
    summary="Synchronize graph delta",
    description="Updates specific crime and criminal records in the Neo4j graph.",
)
async def sync_graph(
    payload: SyncRequest,
    db: DbSession,
    current_user: CurrentUser,
    graph_db: AsyncSession = Depends(get_neo4j_session),
):
    service = GraphService(db, graph_db)
    sync_count = 0
    
    if payload.crime_ids:
        for cid in payload.crime_ids:
            await service.sync_crime(cid)
            sync_count += 1
            
    if payload.criminal_ids:
        for crid in payload.criminal_ids:
            await service.sync_criminal(crid)
            sync_count += 1

    return GraphSyncResponse(
        success=True,
        message="Synchronization finished successfully.",
        synchronized_count=sync_count,
    )


@router.post(
    "/rebuild",
    response_model=GraphSyncResponse,
    summary="Full graph rebuild",
    description="Wipes Neo4j database and rebuilds all nodes and relationships from PostgreSQL.",
)
async def rebuild_graph(
    db: DbSession,
    current_user: CurrentUser,
    graph_db: AsyncSession = Depends(get_neo4j_session),
):
    service = GraphService(db, graph_db)
    counts = await service.rebuild_graph()
    total_synced = counts["crimes_synced"] + counts["criminals_synced"]
    return GraphSyncResponse(
        success=True,
        message=f"Full rebuild complete. Synced {counts['crimes_synced']} crimes, {counts['criminals_synced']} criminals, and {counts['relationships_synced']} relationships.",
        synchronized_count=total_synced,
    )


@router.get(
    "/criminal/{criminal_id}",
    response_model=Dict[str, Any],
    summary="Get criminal node properties",
)
async def get_criminal_node(
    criminal_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    graph_db: AsyncSession = Depends(get_neo4j_session),
):
    service = GraphService(db, graph_db)
    node = await service.repo.get_node_by_label_and_id("Criminal", str(criminal_id))
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Criminal node not found in Neo4j: {criminal_id}",
        )
    return node


@router.get(
    "/crime/{crime_id}",
    response_model=Dict[str, Any],
    summary="Get crime node properties",
)
async def get_crime_node(
    crime_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    graph_db: AsyncSession = Depends(get_neo4j_session),
):
    service = GraphService(db, graph_db)
    node = await service.repo.get_node_by_label_and_id("Crime", str(crime_id))
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crime node not found in Neo4j: {crime_id}",
        )
    return node


@router.get(
    "/network/{criminal_id}",
    response_model=GraphNetworkResponse,
    summary="Get criminal co-offending network",
    description="Traverses co-offenders and associated crimes/victims up to a specified depth limit.",
)
async def get_criminal_network(
    criminal_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    max_depth: int = Query(2, ge=1, le=4, description="Graph traversal depth limit"),
    graph_db: AsyncSession = Depends(get_neo4j_session),
):
    service = GraphService(db, graph_db)
    # Check if starting criminal exists first
    nodes, rels = await service.repo.get_criminal_network(str(criminal_id), max_depth=max_depth)
    return GraphNetworkResponse(nodes=nodes, relationships=rels)


@router.get(
    "/common-associates/{criminal_id}",
    response_model=List[Dict[str, Any]],
    summary="Get common associates (potential co-offenders)",
    description="Finds indirect links: criminals sharing co-offenders who haven't committed crimes directly together.",
)
async def get_common_associates(
    criminal_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
    graph_db: AsyncSession = Depends(get_neo4j_session),
):
    service = GraphService(db, graph_db)
    return await service.get_common_associates(criminal_id)


@router.get(
    "/gang/{gang_name}",
    response_model=GraphNetworkResponse,
    summary="Get gang co-offending network",
    description="Returns the full network of gang members, their commits, and co-offences.",
)
async def get_gang_network(
    gang_name: str,
    db: DbSession,
    current_user: CurrentUser,
    graph_db: AsyncSession = Depends(get_neo4j_session),
):
    service = GraphService(db, graph_db)
    return await service.get_gang_network(gang_name)


@router.get(
    "/shortest-path/{criminal1}/{criminal2}",
    response_model=ShortestPathResponse,
    summary="Find shortest connection path",
    description="Calculates co-offence connections linking two criminals.",
)
async def get_shortest_path(
    criminal1: UUID,
    criminal2: UUID,
    db: DbSession,
    current_user: CurrentUser,
    graph_db: AsyncSession = Depends(get_neo4j_session),
):
    service = GraphService(db, graph_db)
    return await service.get_shortest_path(criminal1, criminal2)


@router.get(
    "/statistics",
    response_model=GraphStatisticsResponse,
    summary="Get graph node and link stats",
)
async def get_statistics(
    db: DbSession,
    current_user: CurrentUser,
    graph_db: AsyncSession = Depends(get_neo4j_session),
):
    service = GraphService(db, graph_db)
    return await service.get_statistics()
