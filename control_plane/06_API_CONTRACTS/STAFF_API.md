# STAFF_API.md

Contrato API para delegacion interna segura en Admin Web.

## Reglas generales

- Prefijo canonico: `/api/v1`.
- Requiere `Authorization: Bearer <session_jwt>`.
- Requiere superficie `X-NODO-Surface: admin_web`.
- Mutaciones requieren `Idempotency-Key`, `reason` no vacio, backend RBAC y audit.
- Solo `super_admin` puede crear invitaciones, activar, suspender, revocar staff o cambiar permisos.
- `admin` puede ver staff si RBAC lo permite; no puede mutar permisos staff.
- `support` y staff delegado no administran staff.
- Las respuestas no exponen tokens, secretos, storage paths, signed URLs persistidas, `account_value` ni datos sensibles completos.

## GET /api/v1/admin/staff

Lista perfiles staff con paginacion cursor.

Query:

- `status`: `active|suspended|revoked`
- `staff_role`: `support_agent|support_lead|operations_readonly|admin|super_admin`
- `q`: busqueda por username/display name enmascarada
- `cursor`
- `limit`

Response 200:

```json
{
  "data": {
    "items": [
      {
        "id": "uuid",
        "user_id": "uuid",
        "display_name": "Nombre",
        "username": "masked",
        "staff_role": "support_agent",
        "status": "active",
        "permission_count": 3,
        "last_activity_at": "timestamp|null",
        "created_at": "timestamp"
      }
    ],
    "next_cursor": "cursor|null"
  },
  "request_id": "req_..."
}
```

## GET /api/v1/admin/staff/{id}

Devuelve detalle staff, permisos activos/revocados recientes y resumen de actividad.

Response 200:

```json
{
  "data": {
    "id": "uuid",
    "user_id": "uuid",
    "staff_role": "support_lead",
    "status": "active",
    "display_name": "Nombre",
    "user_status": "active",
    "permissions": [
      {
        "permission": "view_support_queue",
        "scope": "queue_scope",
        "scope_value": "business_credit",
        "status": "active"
      }
    ],
    "created_at": "timestamp",
    "updated_at": "timestamp"
  },
  "request_id": "req_..."
}
```

## POST /api/v1/admin/staff/invites

Crea invitacion staff o prepara activacion de usuario existente.

Headers:

- `Idempotency-Key`: requerido.

Payload:

```json
{
  "target_user_id": "uuid|null",
  "target_telegram_id": "string|null",
  "target_username": "string|null",
  "staff_role": "support_agent",
  "permissions": [
    {
      "permission": "view_assigned_support_tickets",
      "scope": "assigned_only",
      "scope_value": null
    }
  ],
  "expires_at": "timestamp",
  "reason": "Alta operador soporte turno tarde"
}
```

Response 201:

```json
{
  "data": {
    "invite_id": "uuid",
    "status": "pending",
    "expires_at": "timestamp"
  },
  "request_id": "req_..."
}
```

Rules:

- Al menos uno de `target_user_id`, `target_telegram_id` o `target_username` es requerido.
- No devuelve token/codigo secreto despues de creado.
- No cambia `users.role` por si mismo.
- Audita `staff_invite_created`.

## POST /api/v1/admin/staff/{id}/activate

Activa perfil staff asociado a usuario existente.

Payload:

```json
{
  "reason": "Usuario validado por owner"
}
```

Rules:

- Requiere `users.status = active`.
- Requiere rol base compatible: `support`, `admin` o `super_admin`.
- Audita `staff_activated`.

## POST /api/v1/admin/staff/{id}/suspend

Suspende perfil staff sin bloquear usuario.

Payload:

```json
{
  "reason": "Fin temporal de turno/acceso"
}
```

Rules:

- `active -> suspended`.
- Pierde acceso inmediatamente a capacidades staff.
- Audita `staff_suspended`.

## POST /api/v1/admin/staff/{id}/revoke

Revoca perfil staff sin borrar usuario.

Payload:

```json
{
  "reason": "Fin de relacion operativa"
}
```

Rules:

- `active|suspended -> revoked`.
- No hard delete.
- No afecta tickets historicos ni audit.
- Audita `staff_revoked`.

## POST /api/v1/admin/staff/{id}/permissions

Reemplaza o actualiza conjunto de permisos activos.

Payload:

```json
{
  "permissions": [
    {
      "permission": "reply_support_ticket",
      "scope": "assigned_only",
      "scope_value": null
    }
  ],
  "reason": "Ajuste de cola permitida"
}
```

Rules:

- Solo permisos canonicos de `INTERNAL_STAFF_MASTER.md`.
- Prohibido conceder permisos criticos de usuarios, negocios, creditos, disputas, ordenes o anuncios.
- Conflictos responden `STAFF_PERMISSION_CONFLICT`.
- Audita `staff_permissions_updated`.

## GET /api/v1/admin/staff/{id}/activity

Read model de actividad staff.

Query:

- `cursor`
- `limit`
- `event_type`

Rules:

- Lee de audit/eventos existentes.
- Enmascara datos sensibles.
- Audita `staff_activity_viewed`.

## Errores

- `STAFF_PROFILE_NOT_FOUND`
- `STAFF_INVITE_INVALID`
- `STAFF_INVITE_EXPIRED`
- `STAFF_PERMISSION_DENIED`
- `STAFF_STATUS_INVALID`
- `STAFF_LAST_SUPER_ADMIN_REQUIRED`
- `STAFF_PERMISSION_CONFLICT`
- `STAFF_ASSIGNMENT_INVALID`
- `ADMIN_REASON_REQUIRED`
- `IDEMPOTENCY_KEY_REQUIRED`
- `IDEMPOTENCY_CONFLICT`
- `FORBIDDEN`
- `RATE_LIMITED`
