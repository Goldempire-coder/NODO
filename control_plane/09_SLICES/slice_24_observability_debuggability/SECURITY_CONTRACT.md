# SECURITY_CONTRACT - slice_24_observability_debuggability

## Authority

Observability never grants access. Backend auth/RBAC/ownership/surface policies remain the only authority.

## Required controls

- Ingestion requires auth and surface validation.
- Admin/support search requires backend RBAC.
- Support receives masked values and limited scope.
- Staff requires explicit permission `view_observability_events`.
- All incoming metadata must pass redaction before persistence.
- Unknown fields in event payloads must be rejected or dropped by contract before persistence.
- Route templates only; raw URLs with query params are prohibited.
- Raw headers are prohibited.
- Stack traces are internal logs only, never user responses or frontend events.

## Correlation IDs

Correlation fields are diagnostic only. They must not be trusted for ownership, authorization or resource lookup without backend checks.

## Prohibited captures

- tokens;
- cookies;
- Telegram initData completo;
- secrets;
- private keys;
- seed phrases;
- full tx hashes;
- full phone numbers;
- storage paths;
- signed URLs;
- account values;
- documents;
- complete chat/ticket messages;
- payment instructions.

## Environment gates

- `OBSERVABILITY_INGEST_ENABLED=1` is required for backend persisted frontend events.
- `OBSERVABILITY_MODE` must be one of `disabled`, `local_only`, `persisted`, `logs_only`.
- `NEXT_PUBLIC_OBSERVABILITY_ENABLED` may only enable frontend collection; backend can still reject ingestion.
