# QA

Required coverage:

- payment report versus cancellation and expiration races;
- exact payment amount plus canonical hash, invalid-hash rejection, proof-file
  reuse, proof-order binding, and proof-content hash reuse enforcement;
- payment-instruction reveal versus unconfirmed cancellation race;
- idempotent payment report, cancellation, expiration, and notification effects;
- final active-order-limit revalidation under concurrent creation;
- structured business decline ownership, PIN, state, capacity, ad, audit, and
  notification behavior;
- no pre-payment chat and no sensitive payload exposure;
- reversible migration with invalid historical transaction hash, invalid
  historical proof-content hash, duplicate hash/proof/content-hash, missing
  historical content-hash preflight, and legacy constraint restoration,
  including `admin_cancelled`;
- database-clock use after PostgreSQL row locks and atomic expired-ad
  finalization;
- static evidence that expiration code exists but no scheduler is enabled by
  this slice.

Critical database races require PostgreSQL integration coverage when a disposable
PostgreSQL test harness is available. In-memory tests remain regression coverage,
not proof of PostgreSQL locking behavior.
