# AUDIT_EVENTS.md

Slice 07 required audit events:

- message_created
- message_attachment_uploaded
- dispute_opened
- dispute_message_created

Audit rules:

- Include actor_user_id, actor_role, resource_type, resource_id, old/new state where applicable, reason, request_id/job_id and timestamp.
- Admin sensitive actions require reason.
- Audit logs are append-only.

Slice 07 creates:

- `message_created`
- `message_attachment_uploaded`
- `dispute_opened`
- `dispute_message_created` when a message is created while order/dispute is active in dispute context

Reserved for slice 09 admin resolution:

- `dispute_resolved`

Slice 07 must not emit `dispute_resolved` because it does not resolve disputes.

Not canonical for audit:

- `message_sent`
- `message_blocked`
- `order_completed` in slice 07
