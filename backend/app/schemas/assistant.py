"""
PAC — Assistant Schemas

Pydantic validation schemas for the AI Investigation Assistant API.
All endpoints share the same structured response format so the frontend
can handle responses uniformly.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Request Schemas ────────────────────────────────────────────────────────────

class AssistantChatRequest(BaseModel):
    """General investigator chat request with optional entity context."""
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The investigator's natural language question.",
        example="Why is this criminal classified as High Risk?",
    )
    session_id: str = Field(
        default="default",
        description="Session identifier for multi-turn conversation memory.",
    )
    criminal_id: Optional[str] = Field(
        None,
        description="UUID of the criminal to anchor the query to.",
    )
    crime_id: Optional[str] = Field(
        None,
        description="UUID of the crime / FIR to anchor the query to.",
    )
    district: Optional[str] = Field(
        None,
        description="District name to anchor geo-related queries.",
    )
    gang_name: Optional[str] = Field(
        None,
        description="Gang name to anchor gang-related queries.",
    )


class InvestigationSummaryRequest(BaseModel):
    """Request for a full investigation summary."""
    crime_id: Optional[str] = Field(None, description="UUID of the crime.")
    criminal_id: Optional[str] = Field(None, description="UUID of the criminal.")
    district: Optional[str] = Field(None, description="District name.")
    gang_name: Optional[str] = Field(None, description="Gang name.")
    session_id: str = Field(default="summary")


class PatrolBriefingRequest(BaseModel):
    """Request for district patrol recommendations."""
    district: str = Field(..., description="District name for patrol briefing.")
    session_id: str = Field(default="patrol")


class CrimeSummaryRequest(BaseModel):
    """Request for crime / FIR analytical summary."""
    crime_id: str = Field(..., description="UUID of the crime.")
    session_id: str = Field(default="crime")


class CriminalSummaryRequest(BaseModel):
    """Request for criminal intelligence profile brief."""
    criminal_id: str = Field(..., description="UUID of the criminal.")
    session_id: str = Field(default="criminal")


class ReportRequest(BaseModel):
    """Request to generate a structured intelligence report."""
    report_type: str = Field(
        ...,
        description=(
            "Report type. One of: fir_investigation, criminal_intelligence, "
            "district_crime, hotspot_assessment, gang_intelligence."
        ),
    )
    crime_id: Optional[str] = Field(None)
    criminal_id: Optional[str] = Field(None)
    district: Optional[str] = Field(None)
    gang_name: Optional[str] = Field(None)


# ── Response Schemas ───────────────────────────────────────────────────────────

class AssistantChatResponse(BaseModel):
    """Uniform structured response returned by all assistant endpoints."""
    answer: str = Field(
        ...,
        description="The AI-generated, PAC-grounded investigation response.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score based on available evidence quality.",
    )
    intent: str = Field(
        ...,
        description="Classified intent (e.g. criminal_profile, hotspot_analysis).",
    )
    sources: List[str] = Field(
        default_factory=list,
        description="PAC intelligence modules used to generate this response.",
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="Concrete evidence facts from PAC that support the answer.",
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Operational recommendations for the investigator.",
    )
    follow_up_questions: List[str] = Field(
        default_factory=list,
        description="Suggested follow-up questions for deeper investigation.",
    )
    session_id: str = Field(
        ...,
        description="Session identifier for conversation continuity.",
    )
    is_grounded: bool = Field(
        ...,
        description="True if the response passed all hallucination validation checks.",
    )
    latency_ms: float = Field(
        ...,
        description="Total pipeline latency in milliseconds.",
    )


class ReportResponse(BaseModel):
    """Structured intelligence report response."""
    title: str
    executive_summary: str
    key_findings: List[str]
    evidence: List[str]
    risk_assessment: Dict[str, Any]
    recommendations: List[str]
    suggested_next_actions: List[str]
    metadata: Dict[str, Any]


class AssistantHealthResponse(BaseModel):
    """LLM provider health check response."""
    provider: str
    model: Optional[str] = None
    status: str
    available_modules: List[str]
    supported_intents: List[str]
