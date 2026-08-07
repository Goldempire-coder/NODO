# QA.md

Required QA:

- role matrix
- support readonly blocked from mutations
- approve/reject flows
- audit log filters
- metrics load
- no admin action without reason
- admin opens an investigation only from `payment_rejected`
- admin investigation replay does not duplicate dispute, order/dispute events,
  audit or notifications; changed payload under the same key fails
- support/client/business cannot invoke the admin investigation endpoint
- opening investigation leaves capacity reserved, credits blocked and ad
  `in_order`
- Admin Web exposes `Resolver orden` only for `payment_rejected`, requires a
  reason and confirmation, and never calls a direct order cancel/complete path
- strong confirmation shows the public order code, chosen result and contracted
  credit/capacity/ad effect without exposing the Admin reason to participants
- Admin Web opens the dispute before resolving and refreshes the order after a
  successful resolution
- if resolution fails after opening, Admin Web exposes the created dispute for
  safe retry
- PostgreSQL concurrency allows exactly one administrative opening
- admin dispute resolve requires admin/super_admin, reason and Idempotency-Key
- support cannot resolve disputes
- dispute resolve from `open` and `in_review` follows `STATE_CONTRACT.md`
- dispute resolve with same idempotency key and same payload returns same result
- dispute resolve with same key and different payload fails safely
- dispute resolve creates `dispute_events` and audit log
- dispute resolve applies correct credit/ad effect per resolution type
- dispute resolve notifies client and business once with generic copy and no
  reason, evidence or payment data
- Client detail/history displays `Pago rechazado` only for the safe terminal
  projection derived from `payment_rejected` plus Admin dispute cancellation;
  unrelated `admin_cancelled` orders retain their normal status presentation
- metrics endpoint uses calculated/read-model data and does not require
  `system_metrics` table
- A-04/A-05/A-13 remain slice 08-owned and are only linked/composed
- no `storage_path`, `account_value`, payment instructions, tokens or secrets in
  admin API/frontend/logs
- no escrow/protected-funds/guaranteed-delivery copy

Gate:

- Unit tests for services/state/policies.
- Integration tests for endpoints.
- RBAC/ownership tests.
- Audit event verification.
- Manual smoke for affected screens.
- Builder report must list commands run and tests not run with reason.
