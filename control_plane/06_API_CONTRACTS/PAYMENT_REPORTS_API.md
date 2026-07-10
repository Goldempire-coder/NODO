# PAYMENT_REPORTS_API.md

Contrato canonico para instrucciones de pago y reporte de pago del remitente.

Todas las rutas usan prefijo `/api/v1`.

Rutas legacy como `POST /orders/:id/payment-report` quedan prohibidas como contrato API.

## Endpoints

- `GET /api/v1/orders/{id}/payment-instructions`
- `POST /api/v1/orders/{id}/payment-evidence`
- `POST /api/v1/orders/{id}/payment-report`

## Headers comunes

Lectura sensible:

```txt
Authorization: Bearer <session_jwt>
X-Request-Id: requerido o generado por backend
```

Mutaciones:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-Request-Id: requerido o generado por backend
```

## GET /api/v1/orders/{id}/payment-instructions

Revela instrucciones completas solo al remitente dueno de la orden.

Precondiciones:

- usuario autenticado
- actor `remitter` activo
- orden propia
- `order.status = waiting_payment`
- orden no vencida

Efectos permitidos:

- si `orders.payment_data_revealed_at` es null, setearlo con timestamp actual
- setear `orders.payment_data_revealed_by = current_user.id`
- auditar `payment_instructions_viewed`

Efectos prohibidos:

- no crea `payment_reports`
- no cambia `order.status`
- no consume creditos
- no confirma recepcion del negocio
- no entrega pago movil

Response 200:

```json
{
  "data": {
    "order": {
      "id": "uuid",
      "public_order_code": "NODO-ABC123",
      "status": "waiting_payment",
      "amount_usd": "50.00",
      "amount_bs_calculated": "1825.00",
      "rate_snapshot": "36.500000",
      "payment_report_deadline_at": "timestamp"
    },
    "payment_instructions": {
      "method_type": "zelle",
      "network": null,
      "account_value": "full-value-only-here",
      "account_masked": "***1234",
      "holder_name": "Business Holder"
    },
    "disclaimer": "El cliente paga directamente al negocio. NODO no recibe ni retiene fondos; NODO registra evidencia y estado de la orden."
  },
  "request_id": "req_..."
}
```

Reglas de seguridad:

- `account_value` completo solo aparece en este endpoint para el dueno.
- No aparece en listados, detalle general, logs ni audit metadata.
- `storage_path` nunca aparece en responses.

## POST /api/v1/orders/{id}/payment-evidence

Sube evidencia privada de pago usando `file_assets`.

Precondiciones:

- usuario autenticado
- actor `remitter` activo
- orden propia
- `order.status = waiting_payment`
- orden no vencida
- `Idempotency-Key` obligatorio
- storage privado configurado en runtime normal

Formato:

```txt
multipart/form-data
file: comprobante
file_type: payment_evidence
pending_payment_report_id: uuid opcional
```

Archivo permitido:

- `image/jpeg`
- `image/png`
- `image/webp`
- `application/pdf`

Tamano maximo:

```txt
5242880 bytes
```

Persistencia:

- `file_assets.resource_type = payment_report`
- `file_assets.resource_id = pending_payment_report_id`
- si `pending_payment_report_id` no se envia, el backend genera uno y lo devuelve
- `POST /payment-report` debe crear `payment_reports.id = pending_payment_report_id` cuando use ese proof
- `file_assets.file_type = payment_evidence`
- `file_assets.owner_user_id = orders.remitter_user_id`
- `storage_path` privado obligatorio y nunca expuesto

Response 201:

```json
{
  "data": {
    "file": {
      "id": "uuid",
      "file_type": "payment_evidence",
      "mime_type": "image/png",
      "size_bytes": 120000,
      "created_at": "timestamp"
    },
    "pending_payment_report_id": "uuid"
  },
  "request_id": "req_..."
}
```

Errores:

- `STORAGE_UNAVAILABLE` si storage privado real no esta configurado en runtime normal
- `INVALID_PAYMENT_EVIDENCE` si tipo/tamano no cumple contrato
- `ORDER_EXPIRED` si la orden vencio

## POST /api/v1/orders/{id}/payment-report

Reporta pago del remitente.

Precondiciones:

- usuario autenticado
- actor `remitter` activo
- orden propia
- `order.status = waiting_payment`
- orden no vencida
- `Idempotency-Key` obligatorio
- `payment_type` debe coincidir con `orders.payment_method_snapshot`

Efectos:

- crear `payment_reports.status = submitted`
- setear `orders.status = payment_reported`
- setear `orders.paid_reported_at`
- setear deadlines de respuesta de negocio segun contrato de orden
- crear `order_state_events`
- auditar `payment_reported`

Efectos prohibidos:

- no consume creditos
- no confirma recepcion del negocio
- no entrega pago movil
- no completa la orden
- no cambia `ad.status`; permanece `in_order`
- creditos permanecen bloqueados

### Payload Zelle

Para `orders.payment_method_snapshot = zelle`:

```json
{
  "payment_type": "zelle",
  "payment_reference": "ABC123",
  "payment_sender_name": "Nombre Remitente",
  "payment_sender_account_masked": "***1234",
  "payment_amount": "50.00",
  "proof_file_id": "uuid",
  "pending_payment_report_id": "uuid"
}
```

Reglas:

- `payment_reference` requerido
- `payment_sender_name` requerido
- `payment_sender_account_masked` opcional/recomendado
- `payment_amount` requerido
- `proof_file_id` requerido para Zelle
- `pending_payment_report_id` requerido cuando `proof_file_id` fue creado por `POST /payment-evidence`
- el backend debe validar que `proof_file_id.resource_id = pending_payment_report_id`
- no guardar datos bancarios completos innecesarios

### Payload USDT TRC20

Para `orders.payment_method_snapshot = usdt_trc20`:

```json
{
  "payment_type": "usdt_trc20",
  "tx_hash": "full_tx_hash_internal",
  "network": "TRC20",
  "payment_amount": "50.00",
  "proof_file_id": null
}
```

Reglas:

- `tx_hash` requerido
- `network = TRC20` requerido
- `payment_amount` requerido
- `proof_file_id` opcional porque `tx_hash` es evidencia primaria
- `tx_hash` puede guardarse completo internamente, pero UI/listados/audit usan version masked/truncated

Response 201:

```json
{
  "data": {
    "payment_report": {
      "id": "uuid",
      "order_id": "uuid",
      "status": "submitted",
      "payment_type": "zelle",
      "payment_reference_masked": "***C123",
      "tx_hash_masked": null,
      "payment_amount": "50.00",
      "proof_file_id": "uuid",
      "created_at": "timestamp"
    },
    "order": {
      "id": "uuid",
      "public_order_code": "NODO-ABC123",
      "status": "payment_reported",
      "paid_reported_at": "timestamp"
    },
    "disclaimer": "Reportar pago no significa que el negocio ya confirmo recepcion. El negocio debe revisar y confirmar."
  },
  "request_id": "req_..."
}
```

## Idempotencia

- `payment-report` requiere `Idempotency-Key`.
- `payment-evidence` requiere `Idempotency-Key`.
- Misma key + mismo payload: devolver mismo resultado.
- Misma key + payload distinto: `IDEMPOTENCY_PAYLOAD_MISMATCH` o `IDEMPOTENCY_CONFLICT`.
- No puede duplicar reportes submitted ni evidencias peligrosas.

## Errores esperados

- `UNAUTHENTICATED`
- `FORBIDDEN`
- `VALIDATION_ERROR`
- `RATE_LIMITED`
- `ORDER_NOT_FOUND`
- `ORDER_NOT_OWNED`
- `ORDER_STATUS_INVALID`
- `ORDER_EXPIRED`
- `PAYMENT_REPORT_NOT_ALLOWED`
- `PAYMENT_EVIDENCE_REQUIRED`
- `PAYMENT_REPORT_ALREADY_SUBMITTED`
- `INVALID_PAYMENT_METHOD`
- `INVALID_PAYMENT_EVIDENCE`
- `STORAGE_UNAVAILABLE`
- `STORAGE_UPLOAD_FAILED`
- `IDEMPOTENCY_KEY_REQUIRED`
- `IDEMPOTENCY_CONFLICT`
- `IDEMPOTENCY_PAYLOAD_MISMATCH`

Responses deben seguir `control_plane/06_API_CONTRACTS/ERROR_CONTRACT.md`.
