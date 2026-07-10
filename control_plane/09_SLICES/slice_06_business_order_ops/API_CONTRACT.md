# API_CONTRACT.md

Contrato API del slice: `slice_06_business_order_ops`.

Contrato global canonico:

```txt
control_plane/06_API_CONTRACTS/BUSINESS_ORDERS_API.md
```

## Endpoints autorizados

- `GET /api/v1/business/orders`
- `GET /api/v1/business/orders/{id}`
- `POST /api/v1/business/orders/{id}/confirm-payment`
- `POST /api/v1/business/orders/{id}/reject-payment-report`
- `POST /api/v1/business/orders/{id}/mark-delivered`

## Reglas obligatorias

- Todas las rutas usan `/api/v1`.
- Lecturas requieren auth JWT, actor `business_owner` activo, negocio aprobado y ownership.
- Mutaciones requieren auth JWT, `Idempotency-Key`, RBAC, ownership, state machine, rate limit y audit.
- No filtrar existencia de ordenes ajenas.
- No permitir `business_operator` en MVP.
- No permitir mutaciones admin/support en este slice.
- Responses y errores siguen `ERROR_CONTRACT.md`.
- Payloads, responses, masking, pagination, idempotencia, credit ledger y errores por endpoint estan definidos en `BUSINESS_ORDERS_API.md`.

## Payloads y responses

Este slice no define payloads alternativos. Builder debe implementar exactamente los contratos de:

- `BUSINESS_ORDERS_API.md#GET /api/v1/business/orders`
- `BUSINESS_ORDERS_API.md#GET /api/v1/business/orders/{id}`
- `BUSINESS_ORDERS_API.md#POST /api/v1/business/orders/{id}/confirm-payment`
- `BUSINESS_ORDERS_API.md#POST /api/v1/business/orders/{id}/reject-payment-report`
- `BUSINESS_ORDERS_API.md#POST /api/v1/business/orders/{id}/mark-delivered`

## Campos sensibles prohibidos

- `storage_path`
- tokens
- secretos
- instrucciones completas innecesarias
- `account_value` en list/detail de negocio salvo contrato futuro explicito

