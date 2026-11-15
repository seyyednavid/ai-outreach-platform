"""add users, organisations and per-user Gmail connections

Every company, lead and run now belongs to an organisation. Data that
existed before login is moved into one organisation with no users; the
first user who signs in with LEGACY_OWNER_EMAIL receives it.

Revision ID: f4b8d2e6a913
Revises: e3a7c9d1b582
Create Date: 2026-11-15 16:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f4b8d2e6a913'
down_revision: str | Sequence[str] | None = 'e3a7c9d1b582'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OWNED_TABLES = ("companies", "leads", "outreach_runs")


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
    )
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('email', sa.String(length=320), nullable=True),
        sa.Column(
            'organization_id',
            sa.Integer(),
            sa.ForeignKey('organizations.id'),
            nullable=False,
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
    )
    op.create_index('ix_users_organization_id', 'users', ['organization_id'])

    op.create_table(
        'gmail_connections',
        sa.Column(
            'user_id',
            sa.Uuid(),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            primary_key=True,
        ),
        sa.Column('encrypted_token', sa.Text(), nullable=False),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
    )

    for table in OWNED_TABLES:
        op.add_column(
            table,
            sa.Column('organization_id', sa.Integer(), nullable=True),
        )

    # Existing data goes to one organisation, only if there is any.
    op.execute(
        """
        INSERT INTO organizations (name)
        SELECT 'My organisation'
        WHERE EXISTS (SELECT 1 FROM companies)
           OR EXISTS (SELECT 1 FROM leads)
        """
    )
    for table in OWNED_TABLES:
        op.execute(
            f"UPDATE {table} SET organization_id = "
            "(SELECT min(id) FROM organizations)"
        )

    for table in OWNED_TABLES:
        op.alter_column(table, 'organization_id', nullable=False)
        op.create_foreign_key(
            f'fk_{table}_organization_id',
            table,
            'organizations',
            ['organization_id'],
            ['id'],
        )
        op.create_index(
            f'ix_{table}_organization_id',
            table,
            ['organization_id'],
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table in OWNED_TABLES:
        op.drop_index(f'ix_{table}_organization_id', table_name=table)
        op.drop_constraint(f'fk_{table}_organization_id', table, type_='foreignkey')
        op.drop_column(table, 'organization_id')

    op.drop_table('gmail_connections')
    op.drop_index('ix_users_organization_id', table_name='users')
    op.drop_table('users')
    op.drop_table('organizations')
