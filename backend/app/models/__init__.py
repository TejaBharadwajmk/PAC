"""
PAC Models Package

Import all models here so Alembic autogenerate and SQLAlchemy metadata
can discover every table in one import.
"""

from app.models.user import User, UserRole
from app.models.crime import Crime, CrimeMO, CrimeType, CrimeStatus, CrimeSeverity
from app.models.criminal import Criminal, CrimeCriminal, CrimeRole
from app.models.victim import Victim, CrimeVictim
from app.models.crime_dna import CrimeDNA, EMBEDDING_DIM
from app.models.behaviour import BehaviourProfile
from app.models.prediction import PredictionProfile

__all__ = [
    # User
    "User",
    "UserRole",
    # Crime
    "Crime",
    "CrimeMO",
    "CrimeType",
    "CrimeStatus",
    "CrimeSeverity",
    # Criminal
    "Criminal",
    "CrimeCriminal",
    "CrimeRole",
    # Victim
    "Victim",
    "CrimeVictim",
    # DNA
    "CrimeDNA",
    "EMBEDDING_DIM",
    # Behaviour
    "BehaviourProfile",
    # Prediction
    "PredictionProfile",
]
