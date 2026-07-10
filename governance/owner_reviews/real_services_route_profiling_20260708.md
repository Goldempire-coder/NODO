# Real Services Route Profiling - 2026-07-08

## Estado

PASSED_WITH_PERFORMANCE_FINDINGS

No se declara `READY_FOR_REAL_USE`.

## Cambios al harness

Se agrego profiling por ruta normalizada al harness de smoke/stress:

- `scripts/local_hardening_common.py`
- `scripts/local_smoke.py`

Ahora `metrics` incluye:

- `route_groups`
- `slowest_route_groups`
- `latency_ms` por step
- `route_group` por step

Esto evita que el reporte quede fragmentado en nombres unicos como `stress:orders:create:0`, `stress:orders:create:1`, etc.

## Run ejecutado

Evidencia:

- `evidence/slice_runs/real_services_profile_route_profiling_cap5_20260708_161005.json`
- `evidence/slice_runs/real_services_profile_route_profiling_cap5_20260708_161005.checkpoint.json`

Parametros:

- profile: 10
- cap-businesses: 3
- cap-orders: 5
- workflow-mode: interleaved
- max-duration-seconds: 600

Resultado:

- exit_code: 0
- total_requests: 60
- total_errors: 0
- total_error_rate: 0.0
- invariant violations: todas 0
- businesses: 3
- ads: 5
- orders: 5
- workflow_orders: 3

Metricas globales:

- duracion: 283.149 s
- throughput: 0.2119 req/s
- p50: 4080.7774 ms
- p95: 7175.403 ms
- p99: 7260.0802 ms

## Rutas mas lentas

| Ruta | Count | p50 ms | p95 ms | p99 ms | Avg ms |
|---|---:|---:|---:|---:|---:|
| `POST /api/v1/orders` | 5 | 6512.3173 | 7405.6928 | 7405.6928 | 6446.1432 |
| `POST /api/v1/business/orders/{id}/confirm-payment` | 3 | 7168.4087 | 7260.0802 | 7260.0802 | 6892.958 |
| `POST /api/v1/admin/jobs/expire-and-escalate-orders/dry-run` | 1 | 7175.403 | 7175.403 | 7175.403 | 7175.403 |
| `POST /api/v1/business/ads` | 5 | 6201.5351 | 6366.7601 | 6366.7601 | 6073.0483 |
| `POST /api/v1/businesses/{id}/submit-verification` | 3 | 4404.8686 | 5734.0341 | 5734.0341 | 4837.9303 |
| `POST /api/v1/orders/{id}/payment-report` | 3 | 5272.0596 | 5587.8651 | 5587.8651 | 5119.3485 |
| `GET /api/v1/ads/search` | 5 | 3288.2183 | 5015.4489 | 5015.4489 | 3609.5037 |
| `POST /api/v1/businesses` | 3 | 3979.3686 | 4703.5014 | 4703.5014 | 4073.7636 |
| `POST /api/v1/admin/businesses/{id}/approve` | 3 | 4064.2781 | 4652.3159 | 4652.3159 | 4125.3264 |
| `POST /api/v1/business/orders/{id}/mark-delivered` | 3 | 4604.7827 | 4608.948 | 4608.948 | 4496.4829 |

## Limpieza

Evidencia:

- `evidence/slice_runs/cleanup_dry_run_real_services_profile_route_profiling_cap5_20260708_161005.json`
- `evidence/slice_runs/cleanup_execute_real_services_profile_route_profiling_cap5_20260708_161005.json`
- `evidence/slice_runs/cleanup_postcheck_real_services_profile_route_profiling_cap5_20260708_161005.json`

Postcheck:

- sessions: 0
- businesses: 0
- ads: 0
- orders: 0
- payment_reports: 0
- file_assets: 0

Users sinteticos y audit_logs quedaron retenidos por diseno append-only.

## Lectura

La integridad esta aguantando en estos perfiles pequenos:

- no hay errores HTTP
- no hay balances negativos
- no hay doble consumo/acreditacion
- no hay transiciones invalidas
- no hay timeouts ni deadlocks

El bloqueo real para subir volumen es performance:

- Crear orden esta en ~6.4 s promedio.
- Confirmar pago esta en ~6.9 s promedio.
- Crear anuncio esta en ~6.0 s promedio.
- Search esta en ~3.6 s promedio.
- El job dry-run tambien ronda ~7.1 s incluso con un solo request.

## Recomendacion

No subir todavia a `cap-orders 50`.

Siguiente paso recomendado:

1. Perfilar internamente `POST /api/v1/orders`.
2. Perfilar internamente `POST /api/v1/business/orders/{id}/confirm-payment`.
3. Revisar queries/locks/audit writes/ledger writes en esas rutas.
4. Optimizar primero esas rutas.
5. Repetir `cap-orders 25`.
6. Solo si mejora, subir a `cap-orders 50`.
