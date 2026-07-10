# ADMIN_API.md

Contrato admin MVP. Este archivo cubre:

- verificacion de negocios de `slice_02_business_verification`.
- panel admin funcional de `slice_09_admin_console`.
- solicitudes del Bot Registro Negocios de `slice_14_surface_separation_support_intake`.
- soporte/tickets de `slice_14_surface_separation_support_intake`.

Los endpoints de creditos de `slice_08_credits_referrals` siguen definidos por
`CREDITS_API.md`; slice 09 solo los compone o enlaza en la navegacion admin.

Todas las rutas usan prefijo:

```txt
/api/v1
```

Todas las rutas admin requieren:

- `Authorization: Bearer <session_jwt>`
- rol `admin` o `super_admin` activo para acciones mutantes
- `support` solo lectura o acciones de soporte contratadas
- reason obligatorio para acciones sensibles
- audit log obligatorio

## Slice 14 admin composition

- `GET /api/v1/admin/business-intake`
- `GET /api/v1/admin/business-intake/{id}`
- `POST /api/v1/admin/business-intake/{id}/accept`
- `POST /api/v1/admin/business-intake/{id}/reject`
- `GET /api/v1/admin/support/tickets`
- `POST /api/v1/admin/support/tickets/{id}/escalate`
- `POST /api/v1/admin/support/tickets/{id}/resolve`
- `POST /api/v1/admin/support/tickets/{id}/close`
- `POST /api/v1/admin/businesses/{id}/access-links`
- `POST /api/v1/admin/businesses/{id}/access-links/{link_id}/suspend`
- `POST /api/v1/admin/businesses/{id}/access-links/{link_id}/reactivate`
- `POST /api/v1/admin/businesses/{id}/access-links/{link_id}/revoke`
- `POST /api/v1/admin/businesses/{id}/access-links/{link_id}/block`

Estos endpoints se gobiernan por `BUSINESS_INTAKE_API.md` y `SUPPORT_API.md`.
- RBAC backend
- audit log para acciones sensibles
- errores seguros segun `ERROR_CONTRACT.md`

`support` puede ver segun `RBAC_PERMISSION_MATRIX.md`, pero no ejecutar acciones
mutantes.

### Business access link management

Admin Web controla el acceso final a Mini App Negocio.

#### POST /api/v1/admin/businesses/{id}/access-links

Headers:
- `Authorization`
- `Idempotency-Key`

Payload:
```json
{
  "user_id": "uuid",
  "telegram_id": "123456789",
  "role_in_business": "owner",
  "reason": "string"
}
```

Rules:
- Solo `admin`/`super_admin`.
- Reason obligatorio.
- Business debe existir.
- Para activar acceso operativo, business debe estar `approved` y user debe estar `active`.
- Crea `business_access_links.status = active`.
- No autoriza si el negocio esta `blocked`.
- Audita `business_access_linked`.

#### POST /api/v1/admin/businesses/{id}/access-links/{link_id}/suspend

Payload:
```json
{ "reason": "string" }
```

Rules:
- Solo `admin`/`super_admin`.
- Reason obligatorio.
- Cambia link `active -> suspended`.
- No suspende el negocio completo.
- Audita `business_access_suspended`.

#### POST /api/v1/admin/businesses/{id}/access-links/{link_id}/reactivate

Payload:
```json
{ "reason": "string" }
```

Rules:
- Solo `admin`/`super_admin`.
- Reason obligatorio.
- Cambia link `suspended -> active`.
- Requiere user `active` y business `approved`.
- Audita `business_access_reactivated`.

#### POST /api/v1/admin/businesses/{id}/access-links/{link_id}/revoke

Payload:
```json
{ "reason": "string" }
```

Rules:
- Solo `admin`/`super_admin`.
- Reason obligatorio.
- Cambia link a `revoked`.
- No borra el negocio ni el usuario.
- Audita `business_access_unlinked`.

#### POST /api/v1/admin/businesses/{id}/access-links/{link_id}/block

Payload:
```json
{ "reason": "string" }
```

Rules:
- Solo `admin`/`super_admin`.
- Reason obligatorio.
- Cambia link a `blocked`.
- No borra el negocio ni el usuario.
- Audita `business_access_blocked`.

Listas admin usan cursor pagination. Prohibido offset en tablas calientes.

Campos prohibidos en respuestas admin salvo endpoint de signed URL autorizado:

- `storage_path`
- full payment instructions
- `account_value`
- tokens/secrets
- raw Stripe payloads or secrets
- signed URLs persistidas

## Slice 09 admin console endpoints

### GET /api/v1/admin/dashboard

Permissions:

- admin/super_admin can view.
- support can view when RBAC allows.

Response 200:

```json
{
  "data": {
    "queues": {
      "pending_businesses": 3,
      "pending_credit_purchases": 2,
      "open_disputes": 4
    },
    "orders": {
      "active_count": 120,
      "disputed_count": 4,
      "delivered_waiting_close_count": 9
    },
    "credits": {
      "manual_review_count": 2
    },
    "risk": {
      "businesses_under_review": 1
    }
  },
  "request_id": "req_..."
}
```

Rules:

- Read model only.
- No fake metrics.
- Audit `admin_viewed_dashboard`.
- No sensitive exports.

### GET /api/v1/admin/businesses

Query:

- `verification_status` optional.
- `risk_level` optional.
- `cursor` optional.
- `limit` 1..50.

Response items include masked summary only:

```json
{
  "data": {
    "items": [
      {
        "id": "uuid",
        "business_name": "Casa Cambio Centro",
        "verification_status": "approved",
        "risk_level": "normal",
        "trust_level": "basic",
        "created_at": "timestamp"
      }
    ],
    "next_cursor": "opaque|null"
  },
  "request_id": "req_..."
}
```

### GET /api/v1/admin/orders

Query:

- `status` optional.
- `business_id` optional.
- `remitter_user_id` optional.
- `cursor` optional.
- `limit` 1..50.

Rules:

- No full payment instructions.
- No `account_value`.
- No `storage_path`.
- Return operational summary and capabilities only.

### GET /api/v1/admin/orders/{id}

Rules:

- Admin/super_admin can view operational detail.
- Support can view masked detail if RBAC allows.
- Evidence files are metadata only unless a signed URL endpoint exists.
- No full payment instructions or `account_value`.

### GET /api/v1/admin/audit-logs

Query:

- `event_type` optional.
- `actor_user_id` optional.
- `resource_type` optional.
- `resource_id` optional.
- `cursor` optional.
- `limit` 1..50.

Rules:

- Audit log rows are append-only.
- Response must mask sensitive JSON values.
- Viewing audit logs audits `admin_viewed_audit_logs` once per request.
- Do not recursively log full returned audit payload into the new audit event.

### GET /api/v1/admin/metrics

Rules:

- Metrics are calculated/read-model data from existing tables.
- Slice 09 does not create `system_metrics` table.
- Audit `admin_viewed_metrics`.
- Response must include timestamps/source windows so UI does not imply realtime
  precision when data is stale.

### GET /api/v1/admin/jobs/runs

Permissions:

- admin/super_admin can view.
- support can view read-only when RBAC allows.

Query:

- `job_type` optional; allowed `expire_and_escalate_orders`.
- `status` optional; allowed `started`, `finished`, `failed`, `skipped`,
  `lock_not_acquired`.
- `cursor` optional.
- `limit` 1..50.

Rules:

- Cursor pagination.
- Mask `metadata_json`.
- Do not expose stack traces, SQL, tokens, secrets, `storage_path`,
  `account_value`, signed URLs or full payment instructions.

### GET /api/v1/admin/jobs/runs/{id}

Permissions:

- admin/super_admin can view.
- support can view read-only when RBAC allows.

Rules:

- Returns one masked job run.
- `error_message_safe` may be returned only if it was sanitized.
- `lock_key` must be non-secret.

### POST /api/v1/admin/jobs/expire-and-escalate-orders/dry-run

Permissions:

- admin/super_admin only.
- support receives `FORBIDDEN`.

Headers:

- `Idempotency-Key` required.

Request:

```json
{
  "current_time": "timestamp|null",
  "batch_size": 100
}
```

Rules:

- Dry-run never mutates orders, ads, credits, disputes or notifications.
- Dry-run may create an audit event for admin execution.
- Rate limit applies by actor, route and action_type.
- Errors use `ERROR_CONTRACT.md`.

### POST /api/v1/admin/disputes/{id}/resolve

The canonical contract lives in `DISPUTES_API.md`.

Summary:

- admin/super_admin only.
- support forbidden.
- `Idempotency-Key` required.
- `reason` required.
- allowed `resolution_type`: `remitter_favored`, `business_favored`,
  `cancelled`, `completed`, `keep_under_review`.
- state/credit/ad effects follow `DISPUTE_RESOLUTION_MASTER.md`.
- audit `dispute_resolved` or `dispute_marked_in_review`.
- NODO does not receive, hold, transfer or guarantee funds.

### Admin role management

Admin role mutation is optional in slice 09. If implemented, it must use an
explicit endpoint under `/api/v1/admin/users/{id}/role`, be restricted to
`super_admin`, require `Idempotency-Key`, reason and audit
`admin_role_changed`.

If the endpoint is not implemented, A-10 may display users/remitters read-only
and must not expose role mutation controls.

## GET /api/v1/admin/businesses/pending

Lista negocios con `verification_status = pending`.

Query:

```txt
cursor=opaque|null
limit=1..50
```

Response 200:

```json
{
  "data": {
    "items": [
      {
        "id": "uuid",
        "business_name": "Casa Cambio Centro",
        "rif_masked": "J-***678",
        "phone_masked": "+58*******567",
        "verification_status": "pending",
        "risk_level": "normal",
        "submitted_at": "timestamp|null",
        "created_at": "timestamp"
      }
    ],
    "next_cursor": "opaque|null"
  },
  "request_id": "req_..."
}
```

Rules:

- Cursor pagination.
- No offset en tablas calientes.
- No exponer documentos, storage paths ni datos completos en lista.

## GET /api/v1/admin/businesses/{id}

Detalle admin de verificacion.

Response 200:

```json
{
  "data": {
    "business": {
      "id": "uuid",
      "owner_user_id": "uuid",
      "business_name": "Casa Cambio Centro",
      "rif": "J-12345678-9",
      "address": "string",
      "phone": "+584121234567",
      "country": "VE",
      "verification_status": "pending",
      "trust_level": "new",
      "risk_level": "normal",
      "created_at": "timestamp",
      "updated_at": "timestamp"
    },
    "latest_submission": {
      "id": "uuid",
      "status": "pending",
      "submitted_data": {},
      "submitted_at": "timestamp",
      "reviewed_at": null
    },
    "documents": [
      {
        "id": "uuid",
        "file_type": "rif_document",
        "mime_type": "application/pdf",
        "size_bytes": 12345,
        "created_at": "timestamp"
      }
    ]
  },
  "request_id": "req_..."
}
```

Rules:

- `support` puede ver metadata enmascarada; no obtiene signed URL completa por defecto.
- Abrir documento completo requiere endpoint de signed URL y genera audit event.

## POST /api/v1/admin/businesses/{id}/verification-documents/{file_id}/view-url

Genera signed URL corta para admin/super_admin.

Request:

```json
{
  "reason": "Revision de documento RIF para aprobacion"
}
```

Response 200:

```json
{
  "data": {
    "url": "signed-url",
    "expires_in": 300
  },
  "request_id": "req_..."
}
```

Rules:

- Solo `admin` o `super_admin` activo.
- Reason requerido.
- URL expira maximo en 5 minutos.
- Auditar `verification_document_viewed`.
- Nunca persistir signed URL.

## POST /api/v1/admin/businesses/{id}/approve

Aprueba negocio pendiente.

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-Request-Id: requerido o generado por backend
```

Request:

```json
{
  "reason": "Datos validados manualmente"
}
```

Response 200:

```json
{
  "data": {
    "business": {
      "id": "uuid",
      "verification_status": "approved",
      "approved_at": "timestamp"
    }
  },
  "request_id": "req_..."
}
```

Rules:

- Solo `admin` o `super_admin`.
- Solo si `business.verification_status = pending`.
- `reason` obligatorio y no vacio.
- Actualiza latest submission a `approved`.
- Auditar `business_approved`.
- `support` recibe `FORBIDDEN`.

## POST /api/v1/admin/businesses/{id}/reject

Rechaza negocio pendiente.

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-Request-Id: requerido o generado por backend
```

Request:

```json
{
  "reason": "RIF no coincide con los datos enviados"
}
```

Response 200:

```json
{
  "data": {
    "business": {
      "id": "uuid",
      "verification_status": "rejected"
    }
  },
  "request_id": "req_..."
}
```

Rules:

- Solo `admin` o `super_admin`.
- Solo si `business.verification_status = pending`.
- `reason` obligatorio y no vacio.
- Actualiza latest submission a `rejected`.
- Guardar `admin_reason`.
- Auditar `business_rejected`.
- `support` recibe `FORBIDDEN`.

## Errores esperados

- UNAUTHENTICATED
- FORBIDDEN
- BUSINESS_NOT_FOUND
- BUSINESS_STATUS_INVALID
- ADMIN_REASON_REQUIRED
- BUSINESS_DOCUMENT_NOT_FOUND
- RATE_LIMITED
- IDEMPOTENCY_PAYLOAD_MISMATCH
