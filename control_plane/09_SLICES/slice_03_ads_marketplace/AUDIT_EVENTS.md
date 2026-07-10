# AUDIT_EVENTS.md

Required or expected audit events:

- ad_created
- ad_published
- ad_updated
- ad_paused
- ad_archived
- ad_expired
- credits_held
- credits_released

Audit rules:

- Include actor_user_id, actor_role, resource_type, resource_id, old/new state where applicable, reason, request_id/job_id and timestamp.
- Admin sensitive actions require reason.
- Audit logs are append-only.
