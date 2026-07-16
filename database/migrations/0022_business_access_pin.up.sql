alter table business_access_links
    add column if not exists business_pin_hash text,
    add column if not exists business_pin_set_at timestamptz,
    add column if not exists business_pin_verified_at timestamptz,
    add column if not exists business_pin_unlocked_until timestamptz,
    add column if not exists business_pin_failed_attempts integer not null default 0,
    add column if not exists business_pin_locked_until timestamptz;

alter table business_access_links drop constraint if exists business_access_links_pin_check;
alter table business_access_links
    add constraint business_access_links_pin_check check (
        business_pin_failed_attempts >= 0
        and (
            business_pin_hash is not null
            or (
                business_pin_set_at is null
                and business_pin_verified_at is null
                and business_pin_unlocked_until is null
                and business_pin_locked_until is null
            )
        )
    );

create index if not exists business_access_links_pin_unlock_idx
    on business_access_links (user_id, business_id, business_pin_unlocked_until)
    where status = 'active';
