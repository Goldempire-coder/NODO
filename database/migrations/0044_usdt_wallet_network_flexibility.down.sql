do $$
begin
    if exists (
        select 1
        from business_payment_methods
        where method_type = 'usdt_trc20'
          and (
              network is null
              or network <> 'TRC20'
          )
    ) then
        raise exception using
            errcode = '23514',
            message = 'usdt wallet methods with non-TRC20 or unspecified network require review before rollback';
    end if;
end
$$;

alter table business_payment_methods
    drop constraint if exists business_payment_methods_network_check;

update business_payment_methods
set network = 'trc20'
where method_type = 'usdt_trc20'
  and network = 'TRC20';

alter table business_payment_methods
    add constraint business_payment_methods_network_check check (
        (method_type = 'zelle' and network is null)
        or (method_type = 'usdt_trc20' and network = 'trc20')
    );
