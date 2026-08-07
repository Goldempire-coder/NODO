# SECURITY_CONTRACT.md

Security requirements:

Admin RBAC, super_admin for admin roles, reason required, idempotency for
mutations and audit all sensitive actions.

MVP role `support` may read assigned/admin-visible cases according to RBAC.

Post-MVP `support_readonly` cannot mutate.

Mandatory controls:

- Backend RBAC, not frontend-only hiding.
- Ownership checks for user/business/order resources.
- Rate limits on sensitive or high-traffic endpoints.
- Secrets never in frontend bundle or repo.
- Audit log for sensitive state/data changes.
- `admin` and `super_admin` can resolve disputes in slice 09.
- `support` can view disputes according to RBAC, but cannot resolve.
- Only active `admin` and `super_admin` may open an administrative dispute from
  `payment_rejected`; support and participants are forbidden on that endpoint.
- Administrative opening requires reason and idempotency and atomically writes
  order state, dispute, timeline events and audit `admin_order_dispute_opened`.
- Admin dispute resolution requires `reason`, `Idempotency-Key`, safe errors and
  audit event `dispute_resolved`.
- Admin role changes, if implemented, require `super_admin`, reason and audit
  event `admin_role_changed`.
- No admin response may expose `storage_path`, raw signed URLs, full payment
  instructions, `account_value`, tokens, secrets or raw Stripe webhook data.
- Sensitive exports are not in MVP scope; attempts must return
  `SENSITIVE_EXPORT_BLOCKED` only if an export route is explicitly implemented
  as blocked.

If any control is missing, stop with BLOCKED_BY_SECURITY_GAP.
