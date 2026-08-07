# AUDIT_EVENTS.md

Required or expected audit events:

- admin_viewed_dashboard
- admin_viewed_metrics
- admin_viewed_audit_logs
- business_approved
- business_rejected
- manual_credit_payment_approved
- manual_credit_payment_rejected
- admin_credit_adjustment
- dispute_marked_in_review
- dispute_resolved
- admin_order_dispute_opened
- admin_role_changed only if role management is implemented in this slice

Audit rules:

- Include actor_user_id, actor_role, resource_type, resource_id, old/new state where applicable, reason, request_id/job_id and timestamp.
- Admin sensitive actions require reason.
- Audit logs are append-only.
- Reuse existing business and credit audit event meanings from slices 02 and 08;
  do not duplicate or rename them.
- `dispute_resolved` is emitted by slice 09 terminal dispute resolution, not by
  slice 07.
- `admin_order_dispute_opened` records the Admin/Super Admin action that moves
  one `payment_rejected` order into formal investigation; replay must not append
  it twice.
