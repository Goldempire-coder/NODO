do $$
begin
    execute 'revoke all privileges on schema public from public';
    execute 'revoke all privileges on all tables in schema public from public';
    execute 'revoke all privileges on all sequences in schema public from public';
    execute 'revoke all privileges on all functions in schema public from public';

    execute 'alter default privileges in schema public revoke all on tables from public';
    execute 'alter default privileges in schema public revoke all on sequences from public';
    execute 'alter default privileges in schema public revoke all on functions from public';

    if to_regrole('anon') is not null and to_regrole('authenticated') is not null then
        execute 'revoke all privileges on schema public from anon, authenticated';
        execute 'revoke all privileges on all tables in schema public from anon, authenticated';
        execute 'revoke all privileges on all sequences in schema public from anon, authenticated';
        execute 'revoke all privileges on all functions in schema public from anon, authenticated';

        execute 'alter default privileges in schema public revoke all on tables from anon, authenticated';
        execute 'alter default privileges in schema public revoke all on sequences from anon, authenticated';
        execute 'alter default privileges in schema public revoke all on functions from anon, authenticated';
    end if;
end
$$;

do $$
declare
    table_record record;
begin
    for table_record in
        select format('%I.%I', n.nspname, c.relname) as table_identity
        from pg_class c
        join pg_namespace n on n.oid = c.relnamespace
        where n.nspname = 'public'
          and c.relkind in ('r', 'p')
    loop
        execute format('alter table %s enable row level security', table_record.table_identity);
    end loop;
end
$$;

create or replace function public.nodo_enable_rls_for_new_public_tables()
returns event_trigger
language plpgsql
security definer
set search_path = pg_catalog
as $$
declare
    ddl_command record;
begin
    for ddl_command in
        select *
        from pg_event_trigger_ddl_commands()
        where command_tag in ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO')
          and object_type in ('table', 'partitioned table')
    loop
        if ddl_command.schema_name = 'public' then
            execute format('alter table if exists %s enable row level security', ddl_command.object_identity);
        end if;
    end loop;
end
$$;

revoke all privileges on function public.nodo_enable_rls_for_new_public_tables() from public;

do $$
begin
    if to_regrole('anon') is not null and to_regrole('authenticated') is not null then
        execute 'revoke all privileges on function public.nodo_enable_rls_for_new_public_tables() from anon, authenticated';
    end if;
end
$$;

drop event trigger if exists nodo_enable_rls_on_public_table_create;
create event trigger nodo_enable_rls_on_public_table_create
    on ddl_command_end
    when tag in ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO')
    execute function public.nodo_enable_rls_for_new_public_tables();
