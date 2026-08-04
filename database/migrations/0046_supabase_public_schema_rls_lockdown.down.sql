-- Safety-preserving rollback.
-- This intentionally does not disable RLS or re-grant anon/authenticated access.
-- Reopening public Data API access requires a separate owner-approved migration.

drop event trigger if exists nodo_enable_rls_on_public_table_create;
drop function if exists public.nodo_enable_rls_for_new_public_tables();
