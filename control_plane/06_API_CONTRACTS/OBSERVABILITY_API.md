# OBSERVABILITY_API

Contrato canonico de observabilidad operacional para NODO.

## Principio

Observability diagnostica problemas. No autoriza acciones, no acredita dinero, no reemplaza audit formal y no persiste payloads privados.

## Correlation headers

- `X-Request-Id`
- `X-Correlation-Id`
- `X-NODO-Operation-Id`
- `X-NODO-Surface`

Backend debe aceptar valores validos y generar valores faltantes cuando corresponda. Valores invalidos deben ignorarse o reemplazarse de forma segura.

## Endpoints

- `POST /api/v1/observability/events`
- `GET /api/v1/admin/observability/events`
- `GET /api/v1/admin/observability/events/{id}`
- `GET /api/v1/admin/observability/export`

Los endpoints quedan definidos en `control_plane/09_SLICES/slice_24_observability_debuggability/API_CONTRACT.md`.

## Error safety

Todos los errores deben incluir `request_id` y error code seguro. No exponer stack traces, SQL, rutas internas, headers crudos, tokens ni payloads privados.
