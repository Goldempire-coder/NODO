do $$
begin
    if exists (
        select 1
        from credit_purchases
        where owner_dismissed_at is not null
    ) then
        raise exception '0060 rollback blocked: owner dismissed contract purchases exist; apply an approved transition migration first'
            using errcode = 'P0001';
    end if;
end
$$;

drop index if exists credit_purchases_contract_owner_dismissed_idx;

alter table credit_purchases
    drop column if exists owner_dismissed_by_user_id,
    drop column if exists owner_dismissed_at;
