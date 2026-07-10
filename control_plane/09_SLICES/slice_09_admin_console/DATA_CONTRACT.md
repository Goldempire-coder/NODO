# DATA_CONTRACT.md

Authoritative data touched by this slice:

- admin users/roles
- businesses
- credit_purchases
- disputes
- dispute_events
- orders
- users
- audit_logs
- metrics read model calculated from existing tables
- credits_ledger only when admin dispute resolution or admin credit adjustment creates an audited movement

Rules:

- Use migrations, not manual DB edits.
- Add constraints and indexes for every hot query.
- Never store money/tasa values as float.
- Sensitive fields must be masked in admin/UI where full value is not required.
- Every state-changing record must be traceable through audit_logs or state events.
- Do not create a `system_metrics` table in slice 09. Metrics are calculated
  from `orders`, `businesses`, `credit_purchases`, `disputes`, `audit_logs`,
  `business_metrics`, `job_runs` and `app_metadata` unless a future slice
  explicitly contracts persisted metrics.
- Dispute resolution writes existing `disputes`, `dispute_events`, `orders`,
  `ads`, `credit_wallets`, `credits_ledger` and `audit_logs` only as required by
  `STATE_CONTRACT.md`.
- Admin audit-log reads must not mutate `audit_logs` recursively. Viewing audit
  logs may write one separate audit event `admin_viewed_audit_logs`.

Builder must update 04_DATA/DATA_MODEL_MASTER.md, DATABASE_CONSTRAINTS.md and INDEXES.md if implementation needs fields not listed here.
