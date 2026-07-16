# API_CONTRACT - slice_24_observability_debuggability

## Headers de correlacion

- `X-Request-Id`: generado por frontend o backend. El backend debe generar uno si falta.
- `X-Correlation-Id`: generado por frontend al iniciar sesion de superficie o por backend si falta.
- `X-NODO-Operation-Id`: generado por frontend por accion critica o por backend para operaciones internas.
- `X-NODO-Surface`: requerido para superficies separadas cuando aplique.

Las respuestas API deben devolver `request_id` en body y header. Si existe `correlation_id`, debe propagarse en header seguro.

## POST /api/v1/observability/events

Ingesta de eventos frontend redaccionados.

Auth:

- JWT requerido para Mini App Cliente, Mini App Negocio y Admin Web.
- `X-NODO-Surface` requerido.
- Backend sigue siendo autoridad de identidad, status, surface y RBAC.

Feature flag:

- Deshabilitado por defecto.
- Requiere `OBSERVABILITY_INGEST_ENABLED=1`.
- En produccion queda deshabilitado hasta aprobacion owner posterior.

Body:

```json
{
  "session_id": "ses_uuid",
  "app_version": "staging-24",
  "build_id": "build_24",
  "events": [
    {
      "event_id": "evt_uuid",
      "event_type": "api_request_failed",
      "severity": "warn",
      "timestamp": "2026-07-11T00:00:00Z",
      "request_id": "req_uuid",
      "correlation_id": "corr_uuid",
      "operation_id": "op_uuid",
      "screen": "order-chat",
      "previous_screen": "my-orders",
      "action": "send_message",
      "method": "POST",
      "route_template": "/api/v1/orders/{id}/messages",
      "status_code": 403,
      "duration_ms": 243.5,
      "error_code": "FORBIDDEN",
      "resource_refs": {
        "order_id": "uuid"
      },
      "metadata": {
        "network": "online"
      }
    }
  ]
}
```

Limits:

- Max events per batch: `20`.
- Max event serialized size: `2048` bytes.
- Max request body: `64 KB`.
- Max client-retained breadcrumbs: `50`.
- Max persisted events per session per day: `500`.

Response:

```json
{
  "data": {
    "accepted": 1,
    "rejected": 0
  },
  "request_id": "req_..."
}
```

## GET /api/v1/admin/observability/events

Admin Web diagnostic search.

Auth:

- `super_admin`: full redacted search.
- `admin`: operational redacted search.
- `support`: only tickets/sessions/resources visible under support contract and masked values.
- staff: requires granular permission `view_observability_events` and scope.

Query filters:

- `request_id`
- `correlation_id`
- `operation_id`
- `session_id`
- `surface`
- `user_id_masked`
- `business_id`
- `order_id`
- `ticket_id`
- `credit_purchase_id`
- `telegram_update_id`
- `from`
- `to`
- cursor pagination

The endpoint must not expose raw metadata if role masking disallows it.

## GET /api/v1/admin/observability/events/{id}

Returns one redacted event if RBAC and masking rules allow it.

## GET /api/v1/admin/observability/export

Exports redacted diagnostic evidence for a bounded filter and time window.

Rules:

- Requires admin/super_admin or explicit staff permission.
- Must audit export.
- Must not include secrets, tokens, full messages, full phone, full tx hash, `storage_path`, `account_value` or signed URLs.

## Errors

- `OBSERVABILITY_DISABLED`
- `OBSERVABILITY_EVENT_INVALID`
- `OBSERVABILITY_EVENT_TOO_LARGE`
- `OBSERVABILITY_BATCH_TOO_LARGE`
- `OBSERVABILITY_RATE_LIMITED`
- `OBSERVABILITY_ACCESS_DENIED`
- `OBSERVABILITY_RETENTION_INVALID`
