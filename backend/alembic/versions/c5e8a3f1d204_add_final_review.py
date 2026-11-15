"""add AI review of the human-edited draft

Revision ID: c5e8a3f1d204
Revises: b7d41c2e9a10
Create Date: 2026-11-15 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c5e8a3f1d204'
down_revision: str | Sequence[str] | None = 'b7d41c2e9a10'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'outreach_runs',
        sa.Column('final_review', sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('outreach_runs', 'final_review')
