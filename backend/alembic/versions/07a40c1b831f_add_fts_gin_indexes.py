"""add_fts_gin_indexes

Revision ID: 07a40c1b831f
Revises: 0b84a53574cf
Create Date: 2026-07-22 12:37:32.342575

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = '07a40c1b831f'
down_revision: Union[str, None] = '0b84a53574cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Crimes FTS GIN index (Weighted: Description/MO = A, FIR = B, Address = C, District/Station = D)
    op.execute("""
        CREATE INDEX ix_crimes_fts_simple ON crimes USING gin (
            (
                setweight(to_tsvector('simple', coalesce(description, '')), 'A') ||
                setweight(to_tsvector('simple', coalesce(mo_text, '')), 'A') ||
                setweight(to_tsvector('simple', coalesce(fir_number, '')), 'B') ||
                setweight(to_tsvector('simple', coalesce(location_address, '')), 'C') ||
                setweight(to_tsvector('simple', coalesce(police_station, '')), 'D') ||
                setweight(to_tsvector('simple', coalesce(district, '')), 'D')
            )
        )
    """)

    # 2. CrimeMO FTS GIN index (Weighted: Method/Weapon/MO tags = B, Entry/Target/Tools = C, Escape = D)
    op.execute("""
        CREATE INDEX ix_crime_mo_fts_simple ON crime_mo USING gin (
            (
                setweight(to_tsvector('simple', coalesce(weapon_used, '')), 'B') ||
                setweight(to_tsvector('simple', coalesce(crime_method, '')), 'B') ||
                setweight(to_tsvector('simple', coalesce(entry_method, '')), 'C') ||
                setweight(to_tsvector('simple', coalesce(target_type, '')), 'C') ||
                setweight(to_tsvector('simple', coalesce(escape_method, '')), 'D') ||
                setweight(to_tsvector('simple', coalesce(tools_used::text, '')), 'C') ||
                setweight(to_tsvector('simple', coalesce(modus_operandi_tags::text, '')), 'B')
            )
        )
    """)

    # 3. Criminals FTS GIN index (Weighted: Name = A, Gang/Contact/Aliases = B, Address = C)
    op.execute("""
        CREATE INDEX ix_criminals_fts_simple ON criminals USING gin (
            (
                setweight(to_tsvector('simple', coalesce(name, '')), 'A') ||
                setweight(to_tsvector('simple', coalesce(gang_name, '')), 'B') ||
                setweight(to_tsvector('simple', coalesce(contact_number, '')), 'B') ||
                setweight(to_tsvector('simple', coalesce(aliases::text, '')), 'B') ||
                setweight(to_tsvector('simple', coalesce(address, '')), 'C')
            )
        )
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_criminals_fts_simple")
    op.execute("DROP INDEX IF EXISTS ix_crime_mo_fts_simple")
    op.execute("DROP INDEX IF EXISTS ix_crimes_fts_simple")
