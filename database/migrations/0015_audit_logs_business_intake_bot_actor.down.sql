alter table audit_logs
drop constraint if exists audit_logs_actor_role_check;

alter table audit_logs
add constraint audit_logs_actor_role_check check (
    actor_role is null
    or actor_role in (
        'remitter',
        'business_owner',
        'admin',
        'support',
        'super_admin'
    )
);
