"""
PAC — Crime & CrimeMO Models

Crime: primary FIR record with PostGIS geometry for spatial analysis.
CrimeMO: rule-extracted structured Modus Operandi features (one-to-one with Crime).
"""

import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Float,
    DateTime, ForeignKey, Enum as SAEnum, func, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from app.database import Base


class CrimeType(str, enum.Enum):
    MURDER = "murder"
    ROBBERY = "robbery"
    BURGLARY = "burglary"
    THEFT = "theft"
    CHAIN_SNATCHING = "chain_snatching"
    VEHICLE_THEFT = "vehicle_theft"
    HOUSE_BREAK_IN = "house_break_in"
    AUTO_THEFT = "auto_theft"
    CYBER_CRIME = "cyber_crime"
    ATM_FRAUD = "atm_fraud"
    ASSAULT = "assault"
    KIDNAPPING = "kidnapping"
    FRAUD = "fraud"
    DACOITY = "dacoity"
    EXTORTION = "extortion"
    DRUG_OFFENSE = "drug_offense"
    SEXUAL_ASSAULT = "sexual_assault"
    OTHER = "other"


class CrimeStatus(str, enum.Enum):
    REGISTERED = "registered"
    UNDER_INVESTIGATION = "under_investigation"
    CHARGESHEETED = "chargesheeted"
    SOLVED = "solved"
    CLOSED = "closed"


class CrimeSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Crime(Base):
    __tablename__ = "crimes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fir_number = Column(String(100), unique=True, nullable=False, index=True)

    # Classification
    crime_type = Column(
        SAEnum(
            CrimeType,
            name="crime_type",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        index=True,
    )
    severity = Column(
        SAEnum(
            CrimeSeverity,
            name="crime_severity",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=CrimeSeverity.MEDIUM,
    )
    status = Column(
        SAEnum(
            CrimeStatus,
            name="crime_status",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=CrimeStatus.REGISTERED,
        index=True,
    )

    # Location — district + police station + PostGIS point
    district = Column(String(100), nullable=False, index=True)
    police_station = Column(String(200), nullable=False)
    location_address = Column(String(500))
    latitude = Column(Float)
    longitude = Column(Float)
    # PostGIS POINT geometry for spatial queries (hotspots, radius search)
    geom = Column(Geometry(geometry_type="POINT", srid=4326))

    # Narrative
    description = Column(Text)
    mo_text = Column(Text)  # Full MO narrative — embedded into Crime DNA

    # Temporal
    occurred_at = Column(DateTime(timezone=True), nullable=False, index=True)
    reported_at = Column(DateTime(timezone=True), server_default=func.now())

    # Registration
    registered_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    registered_by_user = relationship(
        "User",
        back_populates="registered_crimes",
        foreign_keys=[registered_by],
    )
    mo_features = relationship(
        "CrimeMO",
        back_populates="crime",
        uselist=False,
        cascade="all, delete-orphan",
    )
    crime_dna = relationship(
        "CrimeDNA",
        back_populates="crime",
        uselist=False,
        cascade="all, delete-orphan",
    )
    criminals = relationship(
        "CrimeCriminal",
        back_populates="crime",
        cascade="all, delete-orphan",
    )
    victims = relationship(
        "CrimeVictim",
        back_populates="crime",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_crimes_district_type", "district", "crime_type"),
        Index("ix_crimes_occurred_district", "occurred_at", "district"),
    )

    def __repr__(self) -> str:
        return f"<Crime fir={self.fir_number!r} type={self.crime_type!r} district={self.district!r}>"


class CrimeMO(Base):
    """
    Structured Modus Operandi features extracted from MO narrative text.

    Populated by the rule-based MO extraction service on crime registration.
    Used alongside Crime DNA (vector embeddings) for similarity ranking and filtering.
    """
    __tablename__ = "crime_mo"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crime_id = Column(
        UUID(as_uuid=True),
        ForeignKey("crimes.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # ── Extracted structured features ──────────────────────
    crime_method = Column(String(100))      # forced_entry | stealth | deception | cyber | confrontation
    entry_method = Column(String(100))      # rear_window | front_door | atm | online | direct
    target_type = Column(String(100))       # individual | residence | shop | vehicle | bank | atm
    weapon_used = Column(String(100))       # knife | gun | iron_rod | none | unknown
    tools_used = Column(JSONB, default=list)                   # ["crowbar", "duplicate_key"]
    time_of_day = Column(String(50))        # morning | afternoon | evening | night | late_night
    day_type = Column(String(50))           # weekday | weekend | holiday | unknown
    planning_level = Column(String(50))     # opportunistic | planned | highly_planned
    gang_involved = Column(Boolean, default=False)
    num_accused = Column(Integer, default=1)
    escape_method = Column(String(100))     # foot | bike | car | auto | unknown
    vehicle_used_in_crime = Column(Boolean, default=False)
    modus_operandi_tags = Column(JSONB, default=list)          # ["two_wheeler", "night_op", "residential"]

    # Extraction metadata
    extraction_method = Column(String(50), default="rule_based")  # rule_based | llm_assisted
    extracted_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    crime = relationship("Crime", back_populates="mo_features")

    def __repr__(self) -> str:
        return f"<CrimeMO crime={self.crime_id!r} method={self.crime_method!r}>"
