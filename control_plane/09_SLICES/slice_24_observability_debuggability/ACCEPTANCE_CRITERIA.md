# ACCEPTANCE_CRITERIA - slice_24_observability_debuggability

Future build can finish `READY_FOR_OWNER_REVIEW` only if:

- request logging middleware emits safe structured logs with request/correlation ids;
- frontend breadcrumbs are redacted and disabled by default;
- backend ingestion is env-gated and rate-limited;
- persisted events have TTL and cleanup;
- Admin Web/support access is RBAC-gated and masked;
- audit and observability remain separate;
- no event/log/evidence contains secrets or private payloads;
- all required tests and scans pass;
- no external observability vendor is introduced without owner approval.

Blocking states:

- `BLOCKED_BY_MISSING_CONTRACT`
- `BLOCKED_BY_SECURITY_GAP`
- `BLOCKED_BY_PRIVACY_RISK`
- `BLOCKED_BY_COST_RISK`
