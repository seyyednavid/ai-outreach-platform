"""add sender details and call-to-action style to companies

Revision ID: d9f2b6a4c731
Revises: c5e8a3f1d204
Create Date: 2026-11-15 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd9f2b6a4c731'
down_revision: str | Sequence[str] | None = 'c5e8a3f1d204'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('companies', sa.Column('sender_name', sa.String(200), nullable=True))
    op.add_column('companies', sa.Column('sender_job_title', sa.String(200), nullable=True))
    op.add_column('companies', sa.Column('sign_off', sa.String(100), nullable=True))
    op.add_column('companies', sa.Column('sender_email', sa.String(320), nullable=True))
    op.add_column('companies', sa.Column('sender_phone', sa.String(50), nullable=True))
    op.add_column(
        'companies',
        sa.Column('cta_type', sa.String(20), server_default='call', nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    for column in ('cta_type', 'sender_phone', 'sender_email', 'sign_off',
                   'sender_job_title', 'sender_name'):
        op.drop_column('companies', column)
