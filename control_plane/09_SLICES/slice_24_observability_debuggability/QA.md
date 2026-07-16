# QA - slice_24_observability_debuggability

## Required tests for future build

- No secrets in logs.
- No tokens in frontend replay events.
- No full Telegram initData in events/logs.
- No `storage_path`.
- No `account_value`.
- No signed URLs.
- No full tx hash when contract requires masking.
- Request logging includes `request_id`.
- Correlation ID propagates backend response and downstream calls where applicable.
- Frontend breadcrumbs redact sensitive fields.
- Session replay is disabled by config.
- Event ingestion is rate-limited.
- Admin/support access respects RBAC.
- Support masking is enforced.
- Retention cleanup is dry-run capable and deletes only expired observability rows.
- Error responses include safe `request_id` and no stack traces.
- Raw URL query params are not logged.
- Unknown event fields are rejected or dropped before persistence.

## Scans

Future build must scan source, build artifacts, evidence and reports for:

- `Authorization`
- `access_token`
- `refresh_token`
- `initData`
- `BOT_TOKEN`
- `BUSINESS_INTAKE_BOT_TOKEN`
- `JWT_SECRET`
- `SUPABASE_SERVICE_ROLE_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `storage_path`
- `account_value`
- `signedUrl`
- `PRIVATE KEY`
- `seed phrase`
- `mnemonic`
