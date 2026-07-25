"""add_audit_logs

Revision ID: a1b2c3d4e5f6
Revises: 07a40c1b831f
Create Date: 2026-07-22 19:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '07a40c1b831f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create audit_action enum type
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'audit_action') THEN
                CREATE TYPE audit_action AS ENUM (
                    'login', 'logout', 'search', 'view',
                    'create', 'update', 'delete', 'reindex', 'ai_query'
                );
            END IF;
        END
        $$;
    """)

    # 2. Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id',           UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id',      UUID(as_uuid=True), nullable=True),
        sa.Column('badge_number', sa.String(50),      nullable=True),
        sa.Column(
            'action',
            sa.Enum(
                'login', 'logout', 'search', 'view',
                'create', 'update', 'delete', 'reindex', 'ai_query',
                name='audit_action',
                create_type=False,   # already created above
            ),
            nullable=False,
        ),
        sa.Column('endpoint',     sa.String(500),      nullable=False),
        sa.Column('method',       sa.String(10),       nullable=False),
        sa.Column('query_text',   sa.Text(),           nullable=True),
        sa.Column('resource_id',  sa.String(255),      nullable=True),
        sa.Column('ip_address',   sa.String(45),       nullable=True),
        sa.Column('user_agent',   sa.String(500),      nullable=True),
        sa.Column('status_code',  sa.Integer(),        nullable=True),
        sa.Column('duration_ms',  sa.Float(),          nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
    )

    # 3. Indexes for admin dashboard query patterns
    op.create_index('ix_audit_logs_user_id',      'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action',        'audit_logs', ['action'])
    op.create_index('ix_audit_logs_created_at',   'audit_logs', ['created_at'])
    op.create_index('ix_audit_logs_user_action',  'audit_logs', ['user_id', 'action'])
    op.create_index('ix_audit_logs_action_created', 'audit_logs', ['action', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_audit_logs_action_created', table_name='audit_logs')
    op.drop_index('ix_audit_logs_user_action',    table_name='audit_logs')
    op.drop_index('ix_audit_logs_created_at',     table_name='audit_logs')
    op.drop_index('ix_audit_logs_action',         table_name='audit_logs')
    op.drop_index('ix_audit_logs_user_id',        table_name='audit_logs')
    op.drop_table('audit_logs')
    op.execute("DROP TYPE IF EXISTS audit_action")
