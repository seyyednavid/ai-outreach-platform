"""enable row level security on every table (blocks the Supabase Data API)

Revision ID: c8e2f5a7b391
Revises: a6c3e9f2d417
Create Date: 2026-11-18 12:00:00.000000

On Supabase, the Data API (/rest/v1) can read tables directly with the
public key that every browser has. This app never uses it: all data goes
through the FastAPI backend, which checks the login and the organisation.

The Data API is switched off in the Supabase dashboard. This is the
second lock: Row Level Security with no policies means the Data API
roles (anon, authenticated) see no rows at all, even if it is switched
on again by mistake.

The backend is not affected: it connects as the tables' owner, and
Row Level Security does not apply to a table's owner.

A migration that creates a new table must enable Row Level Security on it
and list it in its own RLS_TABLES (test_rls_migration checks this).
"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c8e2f5a7b391'
down_revision: str | Sequence[str] | None = 'a6c3e9f2d417'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RLS_TABLES = (
    'organizations',
    'users',
    'gmail_connections',
    'companies',
    'company_products',
    'leads',
    'outreach_runs',
    'alembic_version',
)


def upgrade() -> None:
    """Upgrade schema."""
    for table in RLS_TABLES:
        op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    """Downgrade schema."""
    for table in RLS_TABLES:
        op.execute(f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY')
