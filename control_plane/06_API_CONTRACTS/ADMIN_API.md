# ADMIN_API.md

Contrato admin MVP. Este archivo cubre:

- verificacion de negocios de `slice_02_business_verification`.
- panel admin funcional de `slice_09_admin_console`.
- solicitudes del Bot Registro Negocios de `slice_14_surface_separation_support_intake`.
- soporte/tickets de `slice_14_surface_separation_support_intake`.
- control admin de usuarios y access links de `slice_20A_admin_users_business_control`.
- delegacion interna staff de `slice_20C_internal_staff_roles`.

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
- `GET /api/v1/admin/support/tickets/{id}`
- `POST /api/v1/admin/support/tickets/{id}/messages`
- `POST /api/v1/admin/support/tickets/{id}/assign`
- `POST /api/v1/admin/support/tickets/{id}/escalate`
- `POST /api/v1/admin/support/tickets/{id}/resolve`
- `POST /api/v1/admin/support/tickets/{id}/close`
- `POST /api/v1/admin/support/tickets/{id}/attachments/{file_id}/view-url`
- `GET /api/v1/admin/users`
- `GET /api/v1/admin/users/{id}`
- `POST /api/v1/admin/users/{id}/suspend`
- `POST /api/v1/admin/users/{id}/reactivate`
- `POST /api/v1/admin/users/{id}/block`
- `POST /api/v1/admin/businesses/{id}/suspend`
- `POST /api/v1/admin/businesses/{id}/reactivate`
- `POST /api/v1/admin/businesses/{id}/block`
- `POST /api/v1/admin/businesses/{id}/capacity`
- `GET /api/v1/admin/businesses/{id}/access-links`
- `GET /api/v1/admin/users/{id}/access-links`
- `POST /api/v1/admin/businesses/{id}/access-links`
- `POST /api/v1/admin/businesses/{id}/access-links/{link_id}/suspend`
- `POST /api/v1/admin/businesses/{id}/access-links/{link_id}/reactivate`
- `POST /api/v1/admin/businesses/{id}/access-links/{link_id}/revoke`
- `POST /api/v1/admin/businesses/{id}/access-links/{link_id}/block`

Estos endpoints se gobiernan por `BUSINESS_INTAKE_API.md`, `SUPPORT_API.md` y las secciones admin/access control de este archivo.
- RBAC backend
- audit log para acciones sensibles
- errores seguros segun `ERROR_CONTRACT.md`

`support` puede ver y operar tickets de soporte segun `RBAC_PERMISSION_MATRIX.md`
(responder, asignar, escalar, resolver, cerrar y abrir signed URL de adjunto).
Esa excepcion no autoriza a `support` a aprobar negocios, ajustar creditos,
resolver disputas formales, cambiar ordenes, cambiar anuncios, mutar usuarios o
mutar `business_access_links`.

## Slice 20C staff composition

Los endpoints staff se detallan en `STAFF_API.md` y se componen dentro de Admin Web:

- `GET /api/v1/admin/staff`
- `GET /api/v1/admin/staff/{id}`
- `POST /api/v1/admin/staff/invites`
- `POST /api/v1/admin/staff/{id}/activate`
- `POST /api/v1/admin/staff/{id}/suspend`
- `POST /api/v1/admin/staff/{id}/revoke`
- `POST /api/v1/admin/staff/{id}/permissions`
- `GET /api/v1/admin/staff/{id}/activity`

Rules:

- Solo `super_admin` administra staff/permisos.
- `admin` puede leer staff si RBAC lo permite.
- `support` y staff delegado no administran staff.
- Mutaciones requieren reason, `Idempotency-Key`, backend RBAC y audit.
- Staff delegado no puede recibir permisos criticos de usuarios, negocios, creditos, disputas, ordenes, anuncios o access links.

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

## POST /api/v1/admin/businesses/{id}/capacity

Actualiza la capacidad operativa del negocio.

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-Request-Id: requerido o generado por backend
```

Request:

```json
{
  "trust_level": "new|basic|plus|pro|premium",
  "min_order_amount_usd": "20.00",
  "max_order_amount_usd": "100.00",
  "daily_limit_usd": "1000.00",
  "active_order_limit": 1,
  "reason": "Historial limpio y operaciones exitosas"
}
```

Response 200:

```json
{
  "data": {
    "business": {
      "id": "uuid",
      "trust_level": "plus",
      "min_order_amount_usd": "100.00",
      "max_order_amount_usd": "500.00",
      "daily_limit_usd": "5000.00",
      "active_order_limit": 2
    }
  },
  "request_id": "req_..."
}
```

Rules:

- Solo `admin` o `super_admin`.
- `support` recibe `FORBIDDEN`.
- Reason obligatorio.
- Idempotencia obligatoria.
- `min_order_amount_usd <= max_order_amount_usd`.
- `daily_limit_usd >= max_order_amount_usd`.
- `max_order_amount_usd` no excede $2,000 en MVP.
- `daily_limit_usd` no excede $10,000 en MVP.
- Invalida cache de marketplace porque puede ocultar o habilitar anuncios.
- Auditar `business_capacity_updated` con before/after sin datos sensibles.

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

## POST /api/v1/admin/businesses/{id}/suspend

Suspende temporalmente un negocio completo.

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-Request-Id: requerido o generado por backend
```

Request:

```json
{
  "reason": "Revision temporal por riesgo operacional"
}
```

Response 200:

```json
{
  "data": {
    "business": {
      "id": "uuid",
      "verification_status": "suspended",
      "approved_at": "timestamp"
    }
  },
  "request_id": "req_..."
}
```

Rules:

- Solo `admin` o `super_admin`.
- Solo cambia `approved -> suspended`.
- `reason` obligatorio y no vacio.
- Corta acceso a Business Mini App con `BUSINESS_SUSPENDED`.
- Invalida cache de marketplace para no servir anuncios del negocio suspendido.
- Auditar `business_suspended`.
- `support` recibe `FORBIDDEN`.

## POST /api/v1/admin/businesses/{id}/reactivate

Reactiva un negocio suspendido.

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-Request-Id: requerido o generado por backend
```

Request:

```json
{
  "reason": "Revision completada"
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
- Solo cambia `suspended -> approved`.
- No reactiva negocios `blocked`.
- `reason` obligatorio y no vacio.
- Invalida cache de marketplace.
- Auditar `business_reactivated`.
- `support` recibe `FORBIDDEN`.

## POST /api/v1/admin/businesses/{id}/block

Bloquea un negocio completo.

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-Request-Id: requerido o generado por backend
```

Request:

```json
{
  "reason": "Abuso confirmado"
}
```

Response 200:

```json
{
  "data": {
    "business": {
      "id": "uuid",
      "verification_status": "blocked",
      "approved_at": "timestamp"
    }
  },
  "request_id": "req_..."
}
```

Rules:

- Solo `admin` o `super_admin`.
- Cambia `pending`, `approved`, `rejected` o `suspended` a `blocked`.
- No existe reactivacion desde `blocked` en este contrato.
- `reason` obligatorio y no vacio.
- Corta acceso a Business Mini App con `BUSINESS_BLOCKED`.
- Invalida cache de marketplace para no servir anuncios del negocio bloqueado.
- Auditar `business_blocked`.
- `support` recibe `FORBIDDEN`.

## Slice 20A - Admin users and business access control

### GET /api/v1/admin/users

Lista usuarios para Centro de Operaciones.

Query:

```txt
phone=string|null
telegram_id=int|null
username=string|null
role=remitter|business_owner|admin|super_admin|support|null
status=active|restricted|blocked|dormant|null
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
        "username": "string|null",
        "phone_masked": "+58*******123",
        "telegram_id_masked": "123***789",
        "telegram_id": 123456789,
        "role": "business_owner",
        "status": "active",
        "created_at": "timestamp",
        "last_seen_at": "timestamp|null",
        "linked_business_count": 1
      }
    ],
    "next_cursor": "opaque|null"
  },
  "request_id": "req_..."
}
```

Rules:

- `admin`, `super_admin` y `support` pueden listar segun RBAC.
- `support` recibe solo campos enmascarados y read-only.
- `telegram_id` completo solo se devuelve a `admin`/`super_admin`.
- Cursor pagination; no offset.
- No expone tokens, refresh hashes, session internals, `storage_path`, `account_value` ni secretos.
- Auditar `admin_user_list_viewed` cuando aplique.

### GET /api/v1/admin/users/{id}

Detalle operativo seguro de usuario.

Response 200:

```json
{
  "data": {
    "user": {
      "id": "uuid",
      "username": "string|null",
      "first_name": "string|null",
      "last_name": "string|null",
      "phone_masked": "+58*******123",
      "telegram_id_masked": "123***789",
      "telegram_id": 123456789,
      "role": "business_owner",
      "status": "active",
      "trust_level": "new",
      "created_at": "timestamp",
      "last_seen_at": "timestamp|null"
    },
    "counts": {
      "orders_created": 0,
      "businesses_linked": 1,
      "active_access_links": 1
    },
    "business_access_links": []
  },
  "request_id": "req_..."
}
```

Rules:

- No devuelve tokens, refresh hashes, session internals, raw auth headers ni secretos.
- `support` recibe detalle enmascarado y sin acciones mutantes.
- Auditar `admin_user_detail_viewed` cuando aplique.

### POST /api/v1/admin/users/{id}/suspend

Setea `users.status = restricted`.

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-Request-Id: requerido o generado por backend
```

Request:

```json
{
  "reason": "Revision operacional"
}
```

Rules:

- `admin` y `super_admin` segun protecciones de rol.
- `support` recibe `FORBIDDEN`.
- Reason obligatorio.
- Idempotencia obligatoria.
- Audit `user_suspended`.
- `admin` no suspende usuarios `admin` o `super_admin`.
- Ningun actor suspende el ultimo `super_admin active`.

### POST /api/v1/admin/users/{id}/reactivate

Setea `users.status = active` desde `restricted` o `dormant`.

Rules:

- Reason obligatorio.
- Idempotencia obligatoria.
- Audit `user_reactivated`.
- `blocked -> active` no esta permitido en 20A.

### POST /api/v1/admin/users/{id}/block

Setea `users.status = blocked` desde `active`, `restricted` o `dormant`.

Rules:

- Reason obligatorio.
- Idempotencia obligatoria.
- Audit `user_blocked`.
- No se permite bloquear el ultimo `super_admin active`.

### GET /api/v1/admin/businesses/{id}/access-links

Lista links de acceso de un negocio.

Rules:

- `admin`, `super_admin` y `support` pueden ver.
- `support` ve datos enmascarados/read-only.
- No expone tokens, secretos ni `storage_path`.

### GET /api/v1/admin/users/{id}/access-links

Lista links de acceso asociados a un usuario.

Rules:

- `admin`, `super_admin` y `support` pueden ver.
- `support` ve datos enmascarados/read-only.
- Mutaciones siguen los endpoints de `business_access_links` contratados en 14B1.

## Errores esperados

- UNAUTHENTICATED
- FORBIDDEN
- BUSINESS_NOT_FOUND
- BUSINESS_STATUS_INVALID
- ADMIN_REASON_REQUIRED
- BUSINESS_DOCUMENT_NOT_FOUND
- USER_NOT_FOUND
- USER_STATUS_INVALID
- USER_STATUS_TRANSITION_INVALID
- USER_STATUS_MUTATION_NOT_ALLOWED
- LAST_SUPER_ADMIN_REQUIRED
- BUSINESS_ACCESS_LINK_NOT_FOUND
- BUSINESS_ACCESS_LINK_REQUIRED
- STAFF_PROFILE_NOT_FOUND
- STAFF_INVITE_INVALID
- STAFF_INVITE_EXPIRED
- STAFF_PERMISSION_DENIED
- STAFF_STATUS_INVALID
- STAFF_LAST_SUPER_ADMIN_REQUIRED
- STAFF_PERMISSION_CONFLICT
- STAFF_ASSIGNMENT_INVALID
- RATE_LIMITED
- IDEMPOTENCY_KEY_REQUIRED
- IDEMPOTENCY_CONFLICT
- IDEMPOTENCY_PAYLOAD_MISMATCH
