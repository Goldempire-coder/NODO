# OBSERVABILITY_ARCHITECTURE

## Modelo canonico de correlacion

| Campo | Genera | Propaga | Uso |
|---|---|---|---|
| `request_id` | frontend o backend | `X-Request-Id`, response body/header, logs | rastrear una request |
| `correlation_id` | frontend por sesion de superficie o backend | `X-Correlation-Id`, logs, observability events | unir requests/eventos de una sesion |
| `operation_id` | frontend por accion o backend por operacion critica | `X-NODO-Operation-Id`, logs, events | reconstruir accion end-to-end |
| `session_id` | frontend | observability events | reconstruccion estructurada sin video |
| `surface` | frontend/backend segun superficie | `X-NODO-Surface`, logs, events | diferenciar client/business/admin/bots/workers |
| `app_version` | frontend env/backend config | events/logs | version afectada |
| `build_id` | frontend env/backend config | events/logs | build afectado |
| `user_id_masked` | backend | logs/events/admin view | diagnostico sin exponer identidad completa |
| `business_id` | backend autorizado | logs/events/admin view | diagnostico de negocio |
| `order_id` | backend/autorizado | logs/events/admin view | diagnostico de orden |
| `ticket_id` | backend/autorizado | logs/events/admin view | diagnostico de soporte |
| `credit_purchase_id` | backend/autorizado | logs/events/admin view | diagnostico de credito |
| `tx_hash_masked` | backend | logs/events/admin view | diagnostico on-chain redaccionado |
| `telegram_update_id` | webhook | logs/events | diagnostico bot |
| `webhook_source` | backend | logs/events | origen webhook |

## Headers

- `X-Request-Id`
- `X-Correlation-Id`
- `X-NODO-Operation-Id`
- `X-NODO-Surface`

Headers de correlacion nunca son autoridad de permisos.

## Audit vs Observability

- Audit formal: durable, registra acciones sensibles, cambios de estado y razon.
- Observability: diagnostico operacional con TTL, sampling y redaccion.
- Audit no es session replay.
- Observability no es ledger financiero.

## Proveedor

No se contrata proveedor externo en MVP. La arquitectura usa logs estructurados y almacenamiento backend propio solo si la feature flag lo habilita.
