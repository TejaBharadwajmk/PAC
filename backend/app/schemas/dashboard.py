"""
PAC — Dashboard Summary Schema
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class DashboardCrimeItem(BaseModel):
    id: UUID
    fir_number: str
    crime_type: str
    severity: str
    status: str
    district: str
    police_station: str
    occurred_at: datetime

    class Config:
        from_attributes = True


class DashboardSummaryResponse(BaseModel):
    total_crimes: int
    open_cases: int
    solved_cases: int
    high_severity_cases: int
    hotspots_count: int
    graph_nodes_count: int
    graph_edges_count: int
    recent_crimes: List[DashboardCrimeItem]
    system_status: Dict[str, Any]
    cached_at: Optional[str] = None
