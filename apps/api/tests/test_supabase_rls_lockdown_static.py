from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
UP = ROOT / "database" / "migrations" / "0046_supabase_public_schema_rls_lockdown.up.sql"
DOWN = ROOT / "database" / "migrations" / "0046_supabase_public_schema_rls_lockdown.down.sql"


def test_supabase_public_schema_lockdown_migration_exists() -> None:
    assert UP.exists()
    assert DOWN.exists()


def test_supabase_public_schema_lockdown_revokes_public_data_api_access() -> None:
    sql = UP.read_text(encoding="utf-8").lower()

    assert "revoke all privileges on schema public from public" in sql
    assert "revoke all privileges on all tables in schema public from public" in sql
    assert "revoke all privileges on all sequences in schema public from public" in sql
    assert "revoke all privileges on all functions in schema public from public" in sql
    assert "revoke all privileges on all tables in schema public from anon, authenticated" in sql
    assert "revoke all privileges on all sequences in schema public from anon, authenticated" in sql
    assert "revoke all privileges on all functions in schema public from anon, authenticated" in sql
    assert "alter default privileges in schema public revoke all on functions from public" in sql
    assert "alter default privileges in schema public revoke all on tables from anon, authenticated" in sql
    assert "alter default privileges in schema public revoke all on sequences from anon, authenticated" in sql
    assert "alter default privileges in schema public revoke all on functions from anon, authenticated" in sql


def test_supabase_public_schema_lockdown_enables_rls_without_public_policies() -> None:
    sql = UP.read_text(encoding="utf-8").lower()

    assert "enable row level security" in sql
    assert "pg_class" in sql
    assert "relkind in ('r', 'p')" in sql
    assert "create policy" not in sql
    assert "force row level security" not in sql


def test_supabase_public_schema_lockdown_protects_future_tables() -> None:
    sql = UP.read_text(encoding="utf-8").lower()

    assert "create event trigger nodo_enable_rls_on_public_table_create" in sql
    assert "execute function public.nodo_enable_rls_for_new_public_tables()" in sql
    assert "create table" in sql


def test_supabase_public_schema_lockdown_down_does_not_reopen_public_access() -> None:
    sql = DOWN.read_text(encoding="utf-8").lower()

    forbidden = [
        "grant all",
        "grant select",
        "disable row level security",
        "drop policy",
    ]
    for fragment in forbidden:
        assert fragment not in sql
