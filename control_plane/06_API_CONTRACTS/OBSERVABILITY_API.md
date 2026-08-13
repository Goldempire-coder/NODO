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

## Data/cost protection - Slice 47G1

`POST /api/v1/observability/events` requiere dos cuotas compartidas:

- `30` requests por `user_id + surface` cada `60` segundos;
- `120` requests por IP hasheada cada `60` segundos como respaldo.

Solo `client_mini_app`, `business_mini_app` y `admin_web` son superficies
validas. El rechazo responde `429 OBSERVABILITY_RATE_LIMITED`, no persiste el
batch y no refleja payload, IP ni datos sensibles. Los limites son configurables
por entorno, pero staging/produccion no deben usar los valores altos reservados
para pruebas locales.

En runtime distribuido las cuotas usan Redis. Si Redis no esta disponible, esta
ruta costosa falla cerrada con el mismo error neutral; no degrada a una cuota
local multiplicable por worker.
