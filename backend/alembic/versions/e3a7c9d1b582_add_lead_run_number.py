"""add per-lead run number (Run 1, 2, 3 ... for each lead)

Revision ID: e3a7c9d1b582
Revises: d9f2b6a4c731
Create Date: 2026-11-15 12:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e3a7c9d1b582'
down_revision: str | Sequence[str] | None = 'd9f2b6a4c731'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'outreach_runs',
        sa.Column('lead_run_number', sa.Integer(), nullable=True),
    )
    # Number existing runs per lead, oldest first.
    op.execute(
        """
        UPDATE outreach_runs AS r
        SET lead_run_number = numbered.n
        FROM (
            SELECT id, ROW_NUMBER() OVER (
                PARTITION BY lead_id ORDER BY created_at, id
            ) AS n
            FROM outreach_runs
        ) AS numbered
        WHERE r.id = numbered.id
        """
    )
    op.alter_column('outreach_runs', 'lead_run_number', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('outreach_runs', 'lead_run_number')
