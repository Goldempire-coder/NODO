alter table payment_reports
    drop constraint if exists payment_reports_usdt_required_check;

alter table payment_reports
    add constraint payment_reports_usdt_required_check check (
        payment_type <> 'usdt_trc20'
        or (
            tx_hash is null
            and (network is null or network = 'TRC20')
        )
        or (
            tx_hash is not null
            and network = 'TRC20'
        )
    );
