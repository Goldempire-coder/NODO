# AUDIT_EVENTS.md

Required or expected audit events:

- user_created
- user_login
- user_logout
- session_refreshed
- auth_failed

Audit rules:

- Include actor_user_id, actor_role, resource_type, resource_id, old/new state where applicable, reason, request_id/job_id and timestamp.
- Admin sensitive actions require reason.
- Audit logs are append-only.