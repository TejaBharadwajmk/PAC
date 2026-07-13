"""add_predictive_intelligence

Revision ID: 0b84a53574cf
Revises: 12e7d039ca4c
Create Date: 2026-07-11 15:32:00.274849

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import geoalchemy2


from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = '0b84a53574cf'
down_revision: Union[str, None] = '12e7d039ca4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Modify behaviour_profiles
    op.add_column("behaviour_profiles", sa.Column("prediction_score", sa.Float(), nullable=True))
    op.add_column("behaviour_profiles", sa.Column("prediction_confidence", sa.Float(), nullable=True))
    op.add_column("behaviour_profiles", sa.Column("reoffending_probability", sa.Float(), nullable=True))
    op.add_column("behaviour_profiles", sa.Column("investigation_priority", sa.Float(), nullable=True))
    op.add_column("behaviour_profiles", sa.Column("hotspot_influence_score", sa.Float(), nullable=True))
    op.add_column("behaviour_profiles", sa.Column("district_risk_contribution", sa.Float(), nullable=True))
    op.add_column("behaviour_profiles", sa.Column("prediction_version", sa.String(50), nullable=False, server_default="1.0"))
    op.add_column("behaviour_profiles", sa.Column("prediction_reason_code", sa.String(100), nullable=True))

    # 2. Create prediction_profiles table
    op.create_table(
        "prediction_profiles",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("prediction_type", sa.String(50), nullable=False),
        sa.Column("prediction_score", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("risk_level", sa.String(50), nullable=True),
        sa.Column("prediction_reason_code", sa.String(100), nullable=True),
        sa.Column("prediction_version", sa.String(50), nullable=False, server_default="1.0"),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("evidence", JSONB, nullable=False, server_default="[]"),
        sa.Column("recommendations", JSONB, nullable=False, server_default="[]"),
        sa.Column("score_breakdown", JSONB, nullable=False, server_default="{}"),
        sa.Column("detailed_metrics", JSONB, nullable=False, server_default="{}")
    )
    op.create_index("ix_prediction_profiles_entity_type", "prediction_profiles", ["entity_type"])
    op.create_index("ix_prediction_profiles_entity_id", "prediction_profiles", ["entity_id"])


def downgrade() -> None:
    op.drop_index("ix_prediction_profiles_entity_id")
    op.drop_index("ix_prediction_profiles_entity_type")
    op.drop_table("prediction_profiles")

    op.drop_column("behaviour_profiles", "prediction_score")
    op.drop_column("behaviour_profiles", "prediction_confidence")
    op.drop_column("behaviour_profiles", "reoffending_probability")
    op.drop_column("behaviour_profiles", "investigation_priority")
    op.drop_column("behaviour_profiles", "hotspot_influence_score")
    op.drop_column("behaviour_profiles", "district_risk_contribution")
    op.drop_column("behaviour_profiles", "prediction_version")
    op.drop_column("behaviour_profiles", "prediction_reason_code")
