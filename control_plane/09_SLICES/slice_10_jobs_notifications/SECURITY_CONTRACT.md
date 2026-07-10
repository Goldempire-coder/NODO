# SECURITY_CONTRACT.md

Security requirements:

- Worker uses service credentials stored only in backend environment.
- Admin/ops job endpoints require admin RBAC.
- Redis locks with TTL prevent concurrent processing.
- Job must call official state machine and credit service.
- Job logs cannot contain Telegram tokens, payment evidence URLs, full payment data or secrets.
- Dry-run endpoints are disabled or admin-only in production.
- Redis lock key: `jobs:expire_and_escalate_orders`.
- Redis lock TTL: 5 minutes.
- If lock is not acquired, record `job_runs.status = lock_not_acquired` and do
  not mutate state.
- Admin/ops endpoints:
  - support read-only for job runs.
  - admin/super_admin can execute dry-run only.
  - dry-run never mutates orders, ads, credits, disputes or notifications.
- `job_runs.metadata_json` and `notification_jobs.metadata_json` must be masked
  and must not include `storage_path`, `account_value`, full payment
  instructions, signed URLs, tokens, secrets or raw evidence.

Audit is mandatory for every automatic state transition and every dispute opened by the job.
