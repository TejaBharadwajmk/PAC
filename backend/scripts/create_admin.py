"""
PAC — Admin User Bootstrap Script

Creates the initial system administrator account.
Run this once after applying migrations if not using seed_data.py.

Usage:
  docker exec -it pac_backend python scripts/create_admin.py
  
  Or with custom credentials:
  ADMIN_BADGE=ADMIN001 ADMIN_PASSWORD=MySecret python scripts/create_admin.py
"""

import os
import sys
import uuid
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings
from app.models.user import User, UserRole
from app.core.security import hash_password


BADGE    = os.getenv("ADMIN_BADGE",    "ADMIN001")
PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@2024")
EMAIL    = os.getenv("ADMIN_EMAIL",    "admin@ksp.gov.in")
NAME     = os.getenv("ADMIN_NAME",     "System Administrator")


async def create_admin():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.badge_number == BADGE))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Admin user already exists: badge={BADGE}")
            return

        admin = User(
            id=uuid.uuid4(),
            badge_number=BADGE,
            full_name=NAME,
            email=EMAIL,
            district="Bengaluru Urban",
            police_station="Headquarters",
            role=UserRole.ADMIN,
            hashed_password=hash_password(PASSWORD),
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        print(f"✅ Admin created | badge={BADGE} | password={PASSWORD}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_admin())
