# API_CONTRACT.md

Slice 10 no expone API publica para usuarios finales. Construye workers internos
y endpoints admin/ops protegidos para observabilidad y dry-run.

## Internal job

```txt
expire_and_escalate_orders
```

Inputs:

- current timestamp
- batch size
- dry_run flag for admin/staging only

Effects:

- cancels expired waiting_payment orders
- sends warnings for payment_reported and payment_confirmed
- opens disputes at hard deadlines
- sends delivered reminders
- auto-completes delivered orders after 24h when no dispute exists
- expires ads; Founder expiry retired by Owner on 2026-09-29

Rules:

- `job_type = expire_and_escalate_orders`.
- Uses Redis lock `jobs:expire_and_escalate_orders` with 5 minute TTL.
- If lock is not acquired, records `job_runs.status = lock_not_acquired`.
- Every mutation uses official state machine/credit service.
- Notifications use `notification_jobs.dedupe_key` to prevent duplicates.
- No payload/log/audit metadata may contain `storage_path`, `account_value`,
  full payment instructions, evidence URLs, Telegram tokens, secrets or claims
  that NODO holds/guarantees funds.

## Admin/ops endpoints

All endpoints require `Authorization: Bearer <session_jwt>`.

RBAC:

- `admin` and `super_admin`: can read job runs and execute dry-run.
- `support`: read-only job runs when RBAC allows; cannot execute dry-run.
- `business_owner`, `remitter`, `guest`: forbidden.

### GET /api/v1/admin/jobs/runs

Query:

- `job_type` optional; allowed `expire_and_escalate_orders`.
- `status` optional; allowed `started`, `finished`, `failed`, `skipped`,
  `lock_not_acquired`.
- `cursor` optional.
- `limit` 1..50.

Response 200:

```json
{
  "data": {
    "items": [
      {
        "id": "uuid",
        "job_type": "expire_and_escalate_orders",
        "status": "finished",
        "started_at": "timestamp",
        "finished_at": "timestamp|null",
        "duration_ms": 1234,
        "processed_count": 10,
        "changed_count": 3,
        "skipped_count": 7,
        "failed_count": 0,
        "error_code": null
      }
    ],
    "next_cursor": "opaque|null"
  },
  "request_id": "req_..."
}
```

Rules:

- Cursor pagination only.
- Mask metadata; never expose stack traces, SQL, tokens, secrets,
  `storage_path`, `account_value` or full payment instructions.

### GET /api/v1/admin/jobs/runs/{id}

Response 200:

```json
{
  "data": {
    "id": "uuid",
    "job_type": "expire_and_escalate_orders",
    "status": "failed",
    "lock_key": "jobs:expire_and_escalate_orders",
    "lock_acquired": true,
    "started_at": "timestamp",
    "finished_at": "timestamp|null",
    "duration_ms": 1234,
    "processed_count": 10,
    "changed_count": 3,
    "skipped_count": 6,
    "failed_count": 1,
    "error_code": "NOTIFICATION_SEND_FAILED",
    "error_message_safe": "No se pudo enviar una notificacion temporalmente.",
    "metadata": {}
  },
  "request_id": "req_..."
}
```

Rules:

- `metadata` is masked.
- `lock_key` must be non-secret.

### POST /api/v1/admin/jobs/expire-and-escalate-orders/dry-run

Headers:

- `Authorization: Bearer <session_jwt>`
- `Idempotency-Key` required.

Request:

```json
{
  "current_time": "timestamp|null",
  "batch_size": 100
}
```

Response 200:

```json
{
  "data": {
    "job_type": "expire_and_escalate_orders",
    "dry_run": true,
    "would_process_count": 10,
    "would_change_count": 3,
    "would_notify_count": 2,
    "would_open_dispute_count": 1,
    "would_complete_count": 0
  },
  "request_id": "req_..."
}
```

Rules:

- Dry-run never mutates orders, ads, credits, disputes or notifications.
- Dry-run may create an audit event for admin execution.
- Dry-run is admin/super_admin only.
- Rate limit applies by actor, route and action_type.

Errors:

- `UNAUTHENTICATED`
- `FORBIDDEN`
- `JOB_NOT_FOUND`
- `JOB_CONFIG_INVALID`
- `JOB_LOCK_NOT_ACQUIRED`
- `JOB_RUN_ALREADY_ACTIVE`
- `RATE_LIMITED`
- `VALIDATION_ERROR`
- `INTERNAL_ERROR`

All endpoints require audit logging and safe error responses.
