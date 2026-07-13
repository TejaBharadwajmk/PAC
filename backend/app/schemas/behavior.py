"""
PAC — Behavior Schemas

Pydantic validation schemas for Behavior endpoints.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class BehaviourScoresSchema(BaseModel):
    risk_score: float = Field(..., description="Overall calculated risk score [0.0 - 1.0]")
    risk_level: str = Field(..., description="Overall risk level (LOW / MEDIUM / HIGH)")
    violence_score: float = Field(..., description="Calculated violence tendency score [0.0 - 1.0]")
    gang_affiliation_score: float = Field(..., description="Calculated gang affiliation/co-offending score [0.0 - 1.0]")
    behaviour_consistency_score: float = Field(..., description="Consistency metric across offenses [0.0 - 1.0]")
    serial_offender_probability: float = Field(..., description="Likelihood of being a serial offender [0.0 - 1.0]")
    behaviour_confidence_score: float = Field(..., description="Confidence score in the calculated profile [0.0 - 1.0]")


class BehaviourPatternsSchema(BaseModel):
    primary_crime_type: str = Field(..., description="Dominant crime type committed by the offender")
    preferred_time_slot: str = Field(..., description="Preferred time slot of day (morning/afternoon/evening/night)")
    preferred_day_of_week: str = Field(..., description="Preferred weekday of offenses")
    preferred_season_month: str = Field(..., description="Preferred month of offenses")
    preferred_escape_method: str = Field(..., description="Dominant escape pattern (e.g. bike, car, foot)")
    preferred_target_type: str = Field(..., description="Primary type of targets selected")
    preferred_planning_level: str = Field(..., description="Planning level associated with crimes")
    modus_operandi_tags: List[str] = Field(default_factory=list, description="Top modus operandi tags used")


class BehaviourGeoSchema(BaseModel):
    operating_radius_km: float = Field(..., description="Max distance between committed crime coordinates in km")
    preferred_district: str = Field(..., description="Primary operating district")
    preferred_police_station: str = Field(..., description="Primary operating police station")


class BehaviourProfileResponse(BaseModel):
    """Extensible API response schema consumed directly by front-end and AI assistant."""
    summary: str = Field(..., description="Natural language behavioral summary")
    scores: BehaviourScoresSchema = Field(..., description="Calculated scores and risk levels")
    patterns: BehaviourPatternsSchema = Field(..., description="Modus operandi and operational patterns")
    network: Dict[str, Any] = Field(default_factory=dict, description="Neo4j co-offending network metrics")
    geo: BehaviourGeoSchema = Field(..., description="Geographic intelligence metrics")
    evidence: List[str] = Field(default_factory=list, description="Concrete evidence facts backing the profile")
    recommendations: List[str] = Field(default_factory=list, description="Tactical recommendations for police deployment")
    detailed_metrics: Dict[str, Any] = Field(default_factory=dict, description="Extensible JSON structure containing all breakdowns and explanations")


class HighRiskCriminalsResponse(BaseModel):
    criminal_id: UUID
    name: str
    aliases: List[str]
    risk_score: float
    risk_level: str
    primary_crime_type: str
    last_generated_at: datetime


class BehaviorStatisticsResponse(BaseModel):
    total_profiles: int
    average_risk_score: float
    average_consistency_score: float
    average_operating_radius_km: float
    risk_level_distribution: Dict[str, int]
