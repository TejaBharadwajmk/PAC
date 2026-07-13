"""
PAC — PredictionProfile Model

Stores historical predictive intelligence snapshots.
"""

import uuid
from sqlalchemy import Column, String, Float, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class PredictionProfile(Base):
    """
    Predictive snapshot record of risk forecasts, threat vectors,
    and priority allocations across various entities (criminals, districts, gangs, hotspots).
    """
    __tablename__ = "prediction_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    entity_type = Column(String(50), nullable=False, index=True)      # criminal | district | hotspot | gang | investigation
    entity_id = Column(String(100), nullable=False, index=True)        # UUID or name key
    prediction_type = Column(String(50), nullable=False)              # risk | growth | threat | priority
    
    prediction_score = Column(Float)
    confidence = Column(Float)
    risk_level = Column(String(50))                                    # LOW | MODERATE | HIGH | CRITICAL
    prediction_reason_code = Column(String(100))                       # e.g., SERIAL_PATTERN, ACTIVE_GANG_MEMBER
    prediction_version = Column(String(50), nullable=False, default="1.0")
    
    generated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    evidence = Column(JSONB, nullable=False, default=list)             # list of factual strings
    recommendations = Column(JSONB, nullable=False, default=list)      # list of recommendations
    score_breakdown = Column(JSONB, nullable=False, default=dict)      # detailed sub-weights
    detailed_metrics = Column(JSONB, nullable=False, default=dict)     # custom engine variables

    def __repr__(self) -> str:
        return f"<PredictionProfile entity={self.entity_type}:{self.entity_id} risk={self.risk_level}>"
