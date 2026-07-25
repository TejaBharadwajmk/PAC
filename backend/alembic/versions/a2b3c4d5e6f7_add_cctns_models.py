"""add_cctns_models

Revision ID: a2b3c4d5e6f7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-23 23:21:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type
    cctns_status = postgresql.ENUM('RUNNING', 'SUCCESS', 'PARTIAL_SUCCESS', 'FAILED', name='cctns_sync_status')
    cctns_status.create(op.get_bind(), checkfirst=True)

    # Create cctns_import_logs table
    op.create_table(
        'cctns_import_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('records_extracted', sa.Integer(), nullable=False),
        sa.Column('records_imported', sa.Integer(), nullable=False),
        sa.Column('duplicates_skipped', sa.Integer(), nullable=False),
        sa.Column('failed_count', sa.Integer(), nullable=False),
        sa.Column('status', postgresql.ENUM('RUNNING', 'SUCCESS', 'PARTIAL_SUCCESS', 'FAILED', name='cctns_sync_status', create_type=False), nullable=False),
        sa.Column('error_summary', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create cctns_raw_staging table
    op.create_table(
        'cctns_raw_staging',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cctns_fir_id', sa.String(length=255), nullable=False),
        sa.Column('raw_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_processed', sa.Boolean(), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cctns_raw_staging_cctns_fir_id'), 'cctns_raw_staging', ['cctns_fir_id'], unique=True)
    op.create_index(op.f('ix_cctns_raw_staging_is_processed'), 'cctns_raw_staging', ['is_processed'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_cctns_raw_staging_is_processed'), table_name='cctns_raw_staging')
    op.drop_index(op.f('ix_cctns_raw_staging_cctns_fir_id'), table_name='cctns_raw_staging')
    op.drop_table('cctns_raw_staging')
    op.drop_table('cctns_import_logs')
    sa.Enum(name='cctns_sync_status').drop(op.get_bind(), checkfirst=True)
