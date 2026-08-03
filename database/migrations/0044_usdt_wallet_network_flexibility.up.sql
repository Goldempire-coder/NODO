alter table business_payment_methods
    drop constraint if exists business_payment_methods_network_check;

update business_payment_methods
set network = upper(network)
where method_type = 'usdt_trc20'
  and network is not null;

alter table business_payment_methods
    add constraint business_payment_methods_network_check check (
        (method_type = 'zelle' and network is null)
        or (
            method_type = 'usdt_trc20'
            and (
                network is null
                or network ~ '^[A-Z0-9 _-]{2,32}$'
            )
        )
    );
