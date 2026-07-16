drop index if exists business_access_links_pin_unlock_idx;
alter table business_access_links drop constraint if exists business_access_links_pin_check;
alter table business_access_links
    drop column if exists business_pin_locked_until,
    drop column if exists business_pin_failed_attempts,
    drop column if exists business_pin_unlocked_until,
    drop column if exists business_pin_verified_at,
    drop column if exists business_pin_set_at,
    drop column if exists business_pin_hash;
