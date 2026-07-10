# API_CONTRACT.md

Este slice usa las rutas canonicas definidas en `control_plane/06_API_CONTRACTS/PAYMENT_REPORTS_API.md`.

Endpoints autorizados:

- `GET /api/v1/orders/{id}/payment-instructions`
- `POST /api/v1/orders/{id}/payment-evidence`
- `POST /api/v1/orders/{id}/payment-report`

Rutas legacy sin `/api/v1`, como `POST /orders/:id/payment-report`, quedan prohibidas.

## Reglas comunes

- Auth JWT obligatoria.
- Backend valida RBAC y ownership.
- Solo remitente dueno de la orden.
- Mutaciones requieren `Idempotency-Key`.
- Rate limit obligatorio para reveal/report/upload.
- Responses y errores siguen `ERROR_CONTRACT.md`.
- Frontend no puede saltarse permisos.
- No exponer `storage_path`.
- No exponer instrucciones completas fuera de `GET /payment-instructions`.

## GET /api/v1/orders/{id}/payment-instructions

Precondiciones:

- `order.status = waiting_payment`
- orden no vencida
- actor `remitter` dueno

Efectos:

- setear `payment_data_revealed_at` si esta null
- setear `payment_data_revealed_by`
- auditar `payment_instructions_viewed`

No debe:

- crear payment report
- cambiar status
- consumir creditos
- confirmar negocio

Response incluye instrucciones completas solo para el dueno:

- method_type
- network
- account_value
- account_masked
- holder_name
- amount_usd
- amount_bs_calculated
- rate_snapshot
- public_order_code
- payment_report_deadline_at
- disclaimer

## POST /api/v1/orders/{id}/payment-evidence

Usa `file_assets`.

Reglas:

- owner-only
- private storage
- `file_assets.resource_type = payment_report`
- `file_assets.file_type = payment_evidence`
- upload may return `pending_payment_report_id`
- Zelle report must use matching `pending_payment_report_id` and `proof_file_id`
- `storage_path` privado y no expuesto
- signed URL corta solo para acceso autorizado futuro
- si storage privado real falta en runtime normal, responder `STORAGE_UNAVAILABLE`

## POST /api/v1/orders/{id}/payment-report

Precondiciones:

- `Idempotency-Key` requerido
- `order.status = waiting_payment`
- orden no vencida
- `payment_type` coincide con `orders.payment_method_snapshot`

Efectos:

- crear `payment_reports.status = submitted`
- `orders.status = payment_reported`
- setear `orders.paid_reported_at`
- crear `order_state_events`
- auditar `payment_reported`
- mantener `ad.status = in_order`
- mantener creditos bloqueados

No debe:

- consumir creditos
- confirmar recepcion del negocio
- entregar pago movil
- completar orden

Payloads y responses canonicos viven en `PAYMENT_REPORTS_API.md`.
