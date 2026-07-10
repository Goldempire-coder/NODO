# API_CONTRACT.md

## Endpoints reutilizados

- `GET /api/v1/admin/dashboard`
- `GET /api/v1/admin/metrics`
- `GET /api/v1/admin/businesses`
- `GET /api/v1/admin/businesses/{id}`
- `GET /api/v1/admin/businesses/pending`
- `GET /api/v1/admin/orders`
- `GET /api/v1/admin/orders/{id}`
- `GET /api/v1/admin/disputes`
- `GET /api/v1/admin/disputes/{id}`
- `POST /api/v1/admin/disputes/{id}/resolve`
- `GET /api/v1/admin/audit-logs`
- `GET /api/v1/admin/credit-purchases`
- `POST /api/v1/admin/credit-purchases/{id}/approve`
- `POST /api/v1/admin/credit-purchases/{id}/reject`
- `POST /api/v1/admin/credits/adjust`
- `GET /api/v1/admin/jobs/runs`
- `GET /api/v1/admin/jobs/runs/{id}`
- `POST /api/v1/admin/jobs/expire-and-escalate-orders/dry-run`
- `GET /api/v1/surface/session` cuando este implementado para gate por superficie.

## Reglas

- Todas las rutas activas usan `/api/v1`.
- Admin Web no inventa endpoints.
- Mutaciones sensibles requieren `Idempotency-Key`, reason, rate limit y audit.
- Listas usan cursor pagination.
- Responses admin deben enmascarar datos sensibles.
- `support` read-only salvo contrato explicito.

## Placeholders gobernados

Si `business-intake` o `support/tickets` no estan implementados en backend, Admin Web puede mostrar placeholder gobernado sin mutaciones y sin datos falsos.
