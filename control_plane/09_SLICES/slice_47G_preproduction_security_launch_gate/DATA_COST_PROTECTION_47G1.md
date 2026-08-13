# Slice 47G1 - Data/Cost Protection

Estado: READY_FOR_VALIDATOR_REVIEW_LOCAL

## Alcance

47G1 limita dos rutas de lectura/ingesta capaces de generar costo sostenido:

- `POST /api/v1/observability/events`;
- `GET /api/v1/ads/search`.

No cambia pagos, creditos, ordenes, wallets, uploads, holds, ratings ni UI.

## Cuotas

| Ruta | Clave | Cuota por defecto |
|---|---|---|
| Observability | `user_id + surface` | 30 requests / 60 s |
| Observability | IP hasheada | 120 requests / 60 s |
| Marketplace | `user_id` | 30 requests / 60 s |
| Marketplace | IP hasheada | 120 requests / 60 s |

Observability conserva el maximo existente de 20 eventos por batch. Las IP no
se guardan en claro en claves, logs o respuestas.

## Redis no disponible

En test local se usa un limitador en memoria compartido por proceso. En runtime
distribuido ambas rutas usan una unica instancia `RedisRateLimiter` con
`failure_mode="deny"`. Si Redis falla o permanece dentro del backoff:

- la operacion responde `429` neutral;
- no se ejecuta el repositorio de observability;
- Marketplace no consulta cache/DB para esa busqueda;
- no se usa un fallback local que multiplique la cuota por worker.

Las demas rutas conservan el fallback local previo; ampliarlas queda fuera de
47G1 y requiere una decision por riesgo/disponibilidad.

## Evidencia requerida

- burst por usuario+surface e IP termina en `429`;
- evento rechazado no se persiste y el error no refleja el payload;
- Marketplace conserva respuesta exitosa, filtros y `RATE_LIMITED` neutral;
- el wiring runtime construye Redis en modo cerrado;
- error Redis y periodo de backoff rechazan sin lanzar `500`;
- Ruff, compileall, suite API, `git diff --check` y Secret Guard.

## Limites

No demuestra Redis real, staging multi-worker, Cloudflare IP forwarding ni carga
distribuida. Esas comprobaciones siguen pendientes del gate de infraestructura.
No declarar `READY_FOR_REAL_USE` ni `READY_FOR_PRODUCTION`.
