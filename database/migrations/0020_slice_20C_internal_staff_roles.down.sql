drop index if exists staff_invites_target_username_status_idx;
drop index if exists staff_invites_target_telegram_status_idx;
drop index if exists staff_invites_target_user_status_idx;
drop index if exists staff_invites_status_expires_idx;

drop index if exists staff_permissions_active_unique_idx;
drop index if exists staff_permissions_profile_status_idx;

drop index if exists staff_profiles_one_active_per_user_idx;
drop index if exists staff_profiles_role_status_created_idx;
drop index if exists staff_profiles_user_status_idx;

drop table if exists staff_invites;
drop table if exists staff_permissions;
drop table if exists staff_profiles;
