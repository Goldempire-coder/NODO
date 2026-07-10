# AUDIT_EVENTS.md

Audit events requeridos:

- `payment_confirmed`
- `payment_report_rejected`
- `credits_consumed`
- `ad_archived`
- `order_delivered`

## Rules

- Include `actor_user_id`, `actor_role`, `resource_type`, `resource_id`, old/new state, reason when applicable, request_id/job_id and timestamp.
- Include idempotency key metadata for duplicable mutating actions when applicable.
- Do not store full payment instructions, `account_value`, full evidence, `storage_path`, tokens or secrets.
- Audit logs are append-only.
