# AUDIT_EVENTS.md

Required or expected audit events:

- deploy_started
- deploy_finished
- restore_test_completed
- incident_created
- security_test_completed

Audit rules:

- Include actor_user_id, actor_role, resource_type, resource_id, old/new state where applicable, reason, request_id/job_id and timestamp.
- Admin sensitive actions require reason.
- Audit logs are append-only.