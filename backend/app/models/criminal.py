"""
PAC — Criminal & CrimeCriminal Models

Criminal: accused/suspect master profile.
CrimeCriminal: many-to-many link between crimes and criminals with role metadata.
"""

import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Date, DateTime,
    ForeignKey, Enum as SAEnum, func, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class CrimeRole(str, enum.Enum):
    ACCUSED = "accused"
    SUSPECT = "suspect"
    WITNESS = "witness"


class Criminal(Base):
    __tablename__ = "criminals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    aliases = Column(JSONB, default=list)   # ["Rocky", "Chikku"]

    # Personal
    date_of_birth = Column(Date)
    age = Column(Integer)
    gender = Column(String(20), default="male")

    # Address
    district = Column(String(100), index=True)
    state = Column(String(100), default="Karnataka")
    address = Column(Text)

    # Identity (privacy-safe)
    contact_number = Column(String(20))
    aadhaar_last4 = Column(String(4))   # Only last 4 digits stored

    # Criminal profile
    is_repeat_offender = Column(Boolean, default=False, index=True)
    previous_cases_count = Column(Integer, default=0)
    gang_name = Column(String(200), index=True)
    gang_affiliation = Column(Boolean, default=False)

    # Physical description
    height_cm = Column(Integer)
    build = Column(String(50))           # slim | medium | heavy
    identifying_marks = Column(Text)

    # Status
    is_wanted = Column(Boolean, default=False, index=True)
    is_arrested = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    crimes = relationship(
        "CrimeCriminal",
        back_populates="criminal",
        cascade="all, delete-orphan",
    )
    behaviour_profile = relationship(
        "BehaviourProfile",
        back_populates="criminal",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Criminal name={self.name!r} repeat={self.is_repeat_offender}>"


class CrimeCriminal(Base):
    """Association between crimes and criminals with role and arrest metadata."""

    __tablename__ = "crime_criminals"

    __table_args__ = (
        UniqueConstraint("crime_id", "criminal_id", name="uq_crime_criminal"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crime_id = Column(
        UUID(as_uuid=True),
        ForeignKey("crimes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    criminal_id = Column(
        UUID(as_uuid=True),
        ForeignKey("criminals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(
        SAEnum(
            CrimeRole,
            name="crime_role",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=CrimeRole.ACCUSED,
    )
    is_arrested = Column(Boolean, default=False)
    arrest_date = Column(DateTime(timezone=True))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    crime = relationship("Crime", back_populates="criminals")
    criminal = relationship("Criminal", back_populates="crimes")

    def __repr__(self) -> str:
        return f"<CrimeCriminal crime={self.crime_id!r} criminal={self.criminal_id!r} role={self.role!r}>"
