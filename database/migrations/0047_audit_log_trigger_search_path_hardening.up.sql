create or replace function prevent_audit_logs_mutation()
returns trigger
language plpgsql
set search_path = pg_catalog
as $$
begin
    raise exception 'audit_logs are append-only';
end;
$$;
