# Security Contract

- The backend is authoritative for order amount, state, ownership, deadlines,
  business access, capacity, and active-order limits.
- Conflicting transitions use row locks and expected-state checks.
- Transaction hashes are canonicalized and protected by a database constraint.
- Payment proof files are bound to their upload order and are single-use across
  payment reports.
- Existing invalid transaction hashes, invalid proof-content hashes, duplicate
  hashes, duplicate proof files, and proof files without content hashes must be
  detected before applying the migration.
- PostgreSQL state and expiry decisions use the database clock after the order
  row lock is acquired.
- Revealing payment instructions and cancelling serialize on the order row.
- Logs, audits, events, notifications, and errors must not include full hashes,
  payment instructions, bank data, storage paths, signed URLs, or evidence
  bodies.
- The business decline action has a fixed reason and cannot carry free text.
- Telegram delivery occurs after the order transaction and cannot roll it back.
- Rollback of migration `0039` maps `business_unavailable` cancellation reasons
  to the legacy pre-payment reason. Jobs of the unsupported new notification
  type are preserved, remapped, and pending retries are marked `skipped` before
  restoring the prior constraints. Order events and audit history remain.
- This slice does not treat a payment report as verified payment.
