do $$
begin
    if exists (
        select 1
        from payment_reports
        where payment_type = 'usdt_trc20'
          and (
              tx_hash is null
              or network is distinct from 'TRC20'
          )
    ) then
        raise exception using
            errcode = '23514',
            message = 'usdt payment reports without tx_hash require review before rollback';
    end if;
end
$$;

alter table payment_reports
    drop constraint if exists payment_reports_usdt_required_check;

alter table payment_reports
    add constraint payment_reports_usdt_required_check check (
        payment_type <> 'usdt_trc20'
        or (
            tx_hash is not null
            and network = 'TRC20'
        )
    );
