# ERROR_CASES.md

Expected errors/failures:

- JOB_LOCK_NOT_ACQUIRED
- JOB_RUN_ALREADY_ACTIVE
- JOB_NOT_FOUND
- JOB_CONFIG_INVALID
- ORDER_STATE_CHANGED_DURING_JOB
- STATE_TRANSITION_NOT_ALLOWED
- CREDIT_RELEASE_FAILED
- NOTIFICATION_SEND_FAILED
- TELEGRAM_RATE_LIMITED
- DISPUTE_ALREADY_OPEN
- AUTO_COMPLETE_BLOCKED_BY_DISPUTE
- FORBIDDEN
- RATE_LIMITED

Rules:

- Job failures must be recorded in job_runs.
- Partial failures must not corrupt order/ad/credit state.
- Retry notification failures with backoff.
- Never expose internal job errors to end users without safe copy.
- `JOB_LOCK_NOT_ACQUIRED`, `JOB_RUN_ALREADY_ACTIVE`,
  `ORDER_STATE_CHANGED_DURING_JOB`, `CREDIT_RELEASE_FAILED`,
  `NOTIFICATION_SEND_FAILED`, `TELEGRAM_RATE_LIMITED`,
  `AUTO_COMPLETE_BLOCKED_BY_DISPUTE` and `JOB_CONFIG_INVALID` are internal job
  failures that may appear in admin/ops responses only with safe copy.
- `JOB_NOT_FOUND`, `FORBIDDEN`, `RATE_LIMITED`, `VALIDATION_ERROR` and
  `UNAUTHENTICATED` may appear in admin/ops endpoints according to
  `ERROR_CONTRACT.md`.
- `CREDIT_CONSUME_FAILED` is not expected in slice 10 automatic timers because
  this slice does not consume credits; it only releases credits where the domain
  rules allow release.
