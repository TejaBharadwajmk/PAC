"""
PAC — Victim & CrimeVictim Models

Victim: person affected by a crime.
CrimeVictim: many-to-many link with injury/loss metadata.
"""

import uuid
from sqlalchemy import (
    Column, String, Text, Integer, DateTime,
    ForeignKey, func, Numeric, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Victim(Base):
    __tablename__ = "victims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    age = Column(Integer)
    gender = Column(String(20))
    occupation = Column(String(200))

    # Contact / Address
    district = Column(String(100), index=True)
    address = Column(Text)
    contact_number = Column(String(20))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    crimes = relationship(
        "CrimeVictim",
        back_populates="victim",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Victim name={self.name!r} district={self.district!r}>"


class CrimeVictim(Base):
    """Association between crimes and victims with injury and financial loss data."""

    __tablename__ = "crime_victims"

    __table_args__ = (
        UniqueConstraint("crime_id", "victim_id", name="uq_crime_victim"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crime_id = Column(
        UUID(as_uuid=True),
        ForeignKey("crimes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    victim_id = Column(
        UUID(as_uuid=True),
        ForeignKey("victims.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    injury_type = Column(String(50), default="none")    # none | minor | major | fatal
    loss_amount = Column(Numeric(15, 2))                # in INR
    loss_description = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    crime = relationship("Crime", back_populates="victims")
    victim = relationship("Victim", back_populates="crimes")

    def __repr__(self) -> str:
        return f"<CrimeVictim crime={self.crime_id!r} victim={self.victim_id!r}>"
