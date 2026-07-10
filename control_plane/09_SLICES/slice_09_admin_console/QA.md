# QA.md

Required QA:

- role matrix
- support readonly blocked from mutations
- approve/reject flows
- audit log filters
- metrics load
- no admin action without reason
- admin dispute resolve requires admin/super_admin, reason and Idempotency-Key
- support cannot resolve disputes
- dispute resolve from `open` and `in_review` follows `STATE_CONTRACT.md`
- dispute resolve with same idempotency key and same payload returns same result
- dispute resolve with same key and different payload fails safely
- dispute resolve creates `dispute_events` and audit log
- dispute resolve applies correct credit/ad effect per resolution type
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
