"""add run context snapshot and review override

Revision ID: b7d41c2e9a10
Revises: e6f2b886c6ba
Create Date: 2026-11-13 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b7d41c2e9a10'
down_revision: str | Sequence[str] | None = 'e6f2b886c6ba'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'outreach_runs',
        sa.Column('context', sa.JSON(), nullable=True),
    )
    op.add_column(
        'outreach_runs',
        sa.Column(
            'review_override',
            sa.Boolean(),
            server_default='false',
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('outreach_runs', 'review_override')
    op.drop_column('outreach_runs', 'context')
