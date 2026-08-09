do $$
begin
    if exists (select 1 from business_publication_holds) then
        raise exception '0052 rollback blocked: business_publication_holds contains rows';
    end if;
end
$$;

drop table if exists business_publication_holds;
