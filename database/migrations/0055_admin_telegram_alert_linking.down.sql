drop index if exists admin_telegram_link_codes_user_status_idx;
drop table if exists admin_telegram_link_codes;
drop index if exists users_admin_alert_telegram_id_unique;
alter table users
    drop column if exists admin_alert_telegram_id;
