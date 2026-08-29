do $$
begin
    if exists (select 1 from business_legal_acceptances) then
        raise exception '0061 rollback blocked: business legal acceptances exist';
    end if;
end $$;

drop index if exists business_legal_acceptances_business_idx;
drop index if exists business_legal_acceptances_document_uidx;
drop table if exists business_legal_acceptances;
