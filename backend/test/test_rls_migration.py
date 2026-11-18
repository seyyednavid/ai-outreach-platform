"""Every table must have Row Level Security switched on by a migration.

A table without it would be readable through the Supabase Data API if
that API were ever switched on again. Each migration that switches it
on lists its tables in RLS_TABLES; this test collects them all.
"""
import importlib.util
from pathlib import Path

from app.core.database import Base

VERSIONS = Path(__file__).parent.parent / "alembic" / "versions"


def tables_with_row_level_security() -> set[str]:
    tables: set[str] = set()

    for path in sorted(VERSIONS.glob("*.py")):
        spec = importlib.util.spec_from_file_location(f"migration_{path.stem}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        tables.update(getattr(module, "RLS_TABLES", ()))

    return tables


def test_every_table_has_row_level_security():
    locked = tables_with_row_level_security()
    missing = (set(Base.metadata.tables) | {"alembic_version"}) - locked

    assert not missing, (
        f"Switch on Row Level Security for {sorted(missing)}: in the migration "
        "that creates the table, run ALTER TABLE ... ENABLE ROW LEVEL SECURITY "
        "and list the table in RLS_TABLES"
    )
