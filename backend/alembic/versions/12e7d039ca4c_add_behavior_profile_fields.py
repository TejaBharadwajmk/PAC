"""add_behavior_profile_fields

Revision ID: 12e7d039ca4c
Revises: 002
Create Date: 2026-07-11 15:14:00.942243

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import geoalchemy2


from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = '12e7d039ca4c'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("behaviour_profiles", sa.Column("profile_version", sa.String(50), nullable=False, server_default="1.0"))
    op.add_column("behaviour_profiles", sa.Column("generated_from_crimes", JSONB, nullable=False, server_default="[]"))
    op.add_column("behaviour_profiles", sa.Column("detailed_metrics", JSONB, nullable=False, server_default="{}"))
    op.add_column("behaviour_profiles", sa.Column("preferred_police_station", sa.String(100), nullable=True))
    op.add_column("behaviour_profiles", sa.Column("preferred_day_of_week", sa.String(50), nullable=True))
    op.add_column("behaviour_profiles", sa.Column("preferred_season_month", sa.String(50), nullable=True))
    op.add_column("behaviour_profiles", sa.Column("preferred_escape_method", sa.String(100), nullable=True))
    op.add_column("behaviour_profiles", sa.Column("preferred_modus_operandi", JSONB, nullable=False, server_default="[]"))
    op.add_column("behaviour_profiles", sa.Column("gang_affiliation_score", sa.Float(), nullable=True))
    op.add_column("behaviour_profiles", sa.Column("violence_score", sa.Float(), nullable=True))
    op.add_column("behaviour_profiles", sa.Column("repeat_offender_score", sa.Float(), nullable=True))
    op.add_column("behaviour_profiles", sa.Column("behaviour_consistency_score", sa.Float(), nullable=True))
    op.add_column("behaviour_profiles", sa.Column("escalation_trend", sa.String(50), nullable=True))
    op.add_column("behaviour_profiles", sa.Column("serial_offender_probability", sa.Float(), nullable=True))
    op.add_column("behaviour_profiles", sa.Column("behaviour_confidence_score", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("behaviour_profiles", "profile_version")
    op.drop_column("behaviour_profiles", "generated_from_crimes")
    op.drop_column("behaviour_profiles", "detailed_metrics")
    op.drop_column("behaviour_profiles", "preferred_police_station")
    op.drop_column("behaviour_profiles", "preferred_day_of_week")
    op.drop_column("behaviour_profiles", "preferred_season_month")
    op.drop_column("behaviour_profiles", "preferred_escape_method")
    op.drop_column("behaviour_profiles", "preferred_modus_operandi")
    op.drop_column("behaviour_profiles", "gang_affiliation_score")
    op.drop_column("behaviour_profiles", "violence_score")
    op.drop_column("behaviour_profiles", "repeat_offender_score")
    op.drop_column("behaviour_profiles", "behaviour_consistency_score")
    op.drop_column("behaviour_profiles", "escalation_trend")
    op.drop_column("behaviour_profiles", "serial_offender_probability")
    op.drop_column("behaviour_profiles", "behaviour_confidence_score")
