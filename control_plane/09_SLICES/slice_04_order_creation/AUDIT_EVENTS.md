# AUDIT_EVENTS.md

Required audit events:

- order_created
- order_cancelled
- payment_deadline_extended
- ad_moved_in_order
- order_expired
- credits_released when cancel/expiration releases an ad hold

Required state events:

- order_created
- waiting_payment_extended
- order_cancelled_by_remitter
- order_cancelled_by_timeout

Audit rules:

- Include actor_user_id, actor_role, resource_type, resource_id, old/new state where applicable, reason, request_id/job_id and timestamp.
- Include idempotency key metadata for retryable mutating endpoints when available.
- Admin sensitive actions require reason.
- Audit logs are append-only.
- Do not write full payment instructions, account values, receiver sensitive data, storage paths, tokens or secrets into audit metadata.
