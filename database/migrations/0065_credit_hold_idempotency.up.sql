-- Fail on pre-existing duplicates; never remove or rewrite ledger history.
create unique index credits_ledger_release_ad_unique_idx
    on credits_ledger(related_ad_id)
    where type = 'release';

create unique index credits_ledger_consume_order_unique_idx
    on credits_ledger(related_order_id)
    where type = 'consume';

create unique index credits_ledger_expire_ad_unique_idx
    on credits_ledger(related_ad_id)
    where type = 'expire';
