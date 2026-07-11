"""
PAC — User Model

Officer accounts with role-based access control.
Roles: officer < analyst < supervisor < admin
"""

import uuid
import enum
from sqlalchemy import Column, String, Boolean, Enum as SAEnum, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class UserRole(str, enum.Enum):
    OFFICER = "officer"
    ANALYST = "analyst"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    badge_number = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(200), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    district = Column(String(100), index=True)
    police_station = Column(String(200))
    role = Column(
        SAEnum(UserRole, name="user_role", create_type=False),
        nullable=False,
        default=UserRole.OFFICER,
    )
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    registered_crimes = relationship(
        "Crime",
        back_populates="registered_by_user",
        foreign_keys="Crime.registered_by",
    )

    def __repr__(self) -> str:
        return f"<User badge={self.badge_number!r} role={self.role!r}>"
