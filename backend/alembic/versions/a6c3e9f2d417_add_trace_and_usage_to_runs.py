"""add trace ids and token usage to outreach runs

Revision ID: a6c3e9f2d417
Revises: f4b8d2e6a913
Create Date: 2026-11-15 18:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a6c3e9f2d417'
down_revision: str | Sequence[str] | None = 'f4b8d2e6a913'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('outreach_runs', sa.Column('trace_id', sa.String(length=64), nullable=True))
    op.add_column(
        'outreach_runs',
        sa.Column('recheck_trace_id', sa.String(length=64), nullable=True),
    )
    # Older runs have no recorded usage: they count as zero.
    for column in ('llm_requests', 'input_tokens', 'output_tokens'):
        op.add_column(
            'outreach_runs',
            sa.Column(column, sa.Integer(), server_default='0', nullable=False),
        )
    op.add_column(
        'outreach_runs',
        sa.Column(
            'estimated_cost_usd',
            sa.Numeric(precision=10, scale=6),
            server_default='0',
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    for column in (
        'estimated_cost_usd',
        'output_tokens',
        'input_tokens',
        'llm_requests',
        'recheck_trace_id',
        'trace_id',
    ):
        op.drop_column('outreach_runs', column)
