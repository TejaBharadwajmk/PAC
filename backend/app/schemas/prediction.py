"""
PAC — Prediction Schemas

Pydantic validation schemas for predictive intelligence API payloads.
"""

from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class PredictionScoreBreakdown(BaseModel):
    crime_severity: float = Field(..., description="Weight contribution from offense type severity")
    recency: float = Field(..., description="Weight contribution from elapsed days since last crime")
    repeat_offending: float = Field(..., description="Weight contribution from recidivism counts")
    behaviour_consistency: float = Field(..., description="Weight contribution from MO/district/time consistency")
    violence: float = Field(..., description="Weight contribution from violence index")
    gang_influence: float = Field(..., description="Weight contribution from gang associations")
    network_influence: float = Field(..., description="Weight contribution from Neo4j co-offending centrality")
    hotspot_exposure: float = Field(..., description="Weight contribution from active hotspot presence")
    escalation: float = Field(..., description="Weight contribution from crime severity progression")


class PredictionResponse(BaseModel):
    id: UUID
    entity_type: str = Field(..., description="Entity type: criminal | district | hotspot | gang | investigation")
    entity_id: str = Field(..., description="UUID or name of the entity")
    prediction_type: str = Field(..., description="Prediction target type: risk | growth | threat | priority")
    prediction_score: float = Field(..., description="Calculated prediction index (0.0 - 1.0 or 0.0 - 100.0)")
    confidence: float = Field(..., description="Statistical confidence score (0.0 - 1.0)")
    risk_level: Optional[str] = Field(None, description="Risk or growth category label: LOW | MODERATE | HIGH | CRITICAL")
    prediction_reason_code: Optional[str] = Field(None, description="Primary reason code, e.g. SERIAL_PATTERN")
    prediction_version: str = Field("1.0")
    generated_at: datetime
    evidence: List[str] = Field(default_list=[], description="Traceable evidence facts list")
    recommendations: List[str] = Field(default_list=[], description="Operational recommendation statements")
    score_breakdown: Dict[str, float] = Field(default_dict={}, description="Components score breakdown")
    detailed_metrics: Dict[str, Any] = Field(default_dict={}, description="Engine calculations context")

    class Config:
        from_attributes = True


class DistrictRiskResponse(BaseModel):
    district: str
    risk_score: float
    risk_level: str
    confidence: float
    evidence: List[str]
    recommendations: List[str]
    hotspot_count: int
    crime_volume: int


class GangThreatResponse(BaseModel):
    gang_name: str
    threat_level: str
    threat_score: float
    confidence: float
    evidence: List[str]
    recommendations: List[str]
    member_count: int
    crime_count: int


class HotspotForecastResponse(BaseModel):
    district: str
    growth_trend: str
    score: float
    confidence: float
    evidence: List[str]
    recommendations: List[str]


class InvestigationPriorityResponse(BaseModel):
    crime_id: UUID
    fir_number: str
    priority_score: float
    priority_level: str
    evidence: List[str]
    recommendations: List[str]


class PredictionStatisticsResponse(BaseModel):
    total_criminal_predictions: int
    average_criminal_risk_score: float
    risk_level_distribution: Dict[str, int]
