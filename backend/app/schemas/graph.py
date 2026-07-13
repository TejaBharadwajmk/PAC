"""
PAC — Graph Analytics & Network Intelligence Schemas (Pydantic v2)
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class GraphNodeSchema(BaseModel):
    """General schema for representing a node in the network visualization."""
    id: str = Field(..., description="Unique node ID (UUID or unique string name)")
    label: str = Field(..., description="Primary node label (e.g. Crime, Criminal, Victim, Gang, PoliceStation, District)")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Custom properties on the node")


class GraphRelationshipSchema(BaseModel):
    """General schema for representing a relationship link in the network visualization."""
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: str = Field(..., description="Relationship type (e.g. CRIMINAL_COMMITTED_CRIME, CRIMINAL_ASSOCIATED_WITH_CRIMINAL)")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Custom properties on the relationship link")


class GraphNetworkResponse(BaseModel):
    """Response containing nodes and links for rendering network graphs."""
    nodes: List[GraphNodeSchema]
    relationships: List[GraphRelationshipSchema]


class ShortestPathResponse(BaseModel):
    """Response containing the path and distance between two criminals in the co-offending graph."""
    nodes: List[GraphNodeSchema]
    relationships: List[GraphRelationshipSchema]
    distance: int = Field(..., description="Degrees of separation / path distance")
    found: bool = Field(..., description="Whether a connection path exists")


class GraphStatisticsResponse(BaseModel):
    """Summary counts of all nodes and relationships stored in Neo4j."""
    node_counts: Dict[str, int] = Field(..., description="Count of nodes grouped by label")
    relationship_counts: Dict[str, int] = Field(..., description="Count of relationships grouped by type")


class GraphSyncResponse(BaseModel):
    """Success response for synchronization requests."""
    success: bool
    message: str
    synchronized_count: int
