# API_CONTRACT.md

## Endpoints sensibles a verificar

Business:

- `GET /api/v1/surface/session`
- `GET /api/v1/business/payment-methods`
- `POST /api/v1/business/payment-methods`
- `PATCH /api/v1/business/payment-methods/{id}`
- `DELETE /api/v1/business/payment-methods/{id}`
- `PATCH /api/v1/business/availability`
- PIN setup/verify/lock endpoints existentes.

Ads:

- `GET /api/v1/business/ads`
- `POST /api/v1/business/ads`
- `PUT /api/v1/business/ads/{id}`
- `POST /api/v1/business/ads/{id}/pause`
- `POST /api/v1/business/ads/{id}/reactivate`
- `POST /api/v1/business/ads/{id}/archive`
- `POST /api/v1/business/ads/{id}/republish`
- marketplace search/detail/order creation affected by deleted payment method and offline business.

Credits:

- `GET /api/v1/business/credits/wallet`
- `POST /api/v1/business/credits/base-payment`
- `GET /api/v1/business/credits/purchases/{id}`
- `POST /api/v1/business/credits/purchases/{id}/tx-hash`

Orders:

- `GET /api/v1/business/orders`
- `GET /api/v1/business/orders/{id}`
- `POST /api/v1/business/orders/{id}/confirm-payment`
- `POST /api/v1/orders/{id}/disputes`
- `POST /api/v1/business/orders/{id}/reject-payment-report` (legacy; no muta)
- `POST /api/v1/business/orders/{id}/mark-delivered`

## Reglas API

- Toda mutacion sensible debe usar idempotency key cuando corresponda.
- Toda respuesta de error debe usar contrato `error.code`.
- No cambiar shape JSON sin contrato de API.
- No exponer `account_value`, wallet privada, storage path, signed URL ni tokens.
- Metodo de cobro visible para negocio puede incluir valor completo solo si es necesario para editar; no debe llegar al marketplace cliente completo sin mascara.
- Respuestas de orden para negocio no deben exponer datos de otro negocio.

## Evidencia

- tests backend directos;
- tests de unauthorized/forbidden;
- tests de duplicate/idempotency;
- tests de stale/deleted payment method;
- tests offline business.
