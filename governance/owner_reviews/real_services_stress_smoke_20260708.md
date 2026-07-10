# REAL SERVICES STRESS SMOKE - 2026-07-08

## Estado

PASSED_WITH_PERFORMANCE_FINDINGS

No se declara READY_FOR_REAL_USE.

## Alcance

Pruebas ejecutadas contra app local usando servicios reales configurados en staging:

- Supabase/PostgreSQL real
- Redis real
- Backend NODO local en memoria via test app
- Storage adapter configurado por env de staging

No fue un load test HTTP directo contra Railway. Esta fase valida reglas, concurrencia, DB, Redis, idempotencia y transiciones con servicios reales sin saturar el deploy.

## Cambio Necesario En Harness

La primera prueba de concurrencia falló correctamente con:

`BUSINESS_ACCESS_LINK_REQUIRED`

Motivo: el harness viejo aprobaba negocios sintéticos pero no creaba `business_access_links`, y la regla nueva de 14B1 exige vínculo activo para operar como negocio.

Corrección aplicada:

- `scripts/local_smoke.py` ahora crea un access link admin después de aprobar el negocio sintético.
- No se relajó la regla de negocio.
- Validación: `python -m compileall scripts/local_smoke.py scripts/stress_local.py scripts/concurrency_local.py` OK.

## Fix De Performance Aplicado Al Job Dry-Run

Durante el stress funcional, `POST /api/v1/admin/jobs/expire-and-escalate-orders/dry-run?batch_size=500` tardó 156994.8032 ms.

Hallazgo:

- En `dry_run`, `_cancel_waiting_payment` hacía `get_ad(order.ad_id)` antes de revisar `dry_run`.
- Eso generaba consultas innecesarias por cada orden `waiting_payment` vencida.

Corrección aplicada:

- `apps/api/app/modules/jobs/worker.py` ahora retorna inmediatamente en dry-run antes de consultar el anuncio.
- También se evitó consultar disputa abierta para órdenes `delivered` salvo cuando `auto_complete_at` ya venció.

Validación:

- `python -m pytest apps/api/tests/test_jobs_notifications.py -q` con `PYTHONPATH=apps/api`: `7 passed, 1 warning`.
- `python -m compileall apps/api/app/modules/jobs`: OK.

Perfil posterior con lock en memoria y servicios reales:

- Evidencia: `evidence/slice_runs/job_worker_profile_inmemory_lock_20260708.json`
- processed_count: 482
- changed_count: 472
- failed_count: 0
- elapsed: 12009.235 ms
- `_cancel_waiting_payment`: 442 llamadas, 0.456 ms total.
- cuello restante: `_handle_delivered`, 30 llamadas, 8981.533 ms total.

Conclusión del fix:

- Se eliminó el N+1 innecesario sobre anuncios en dry-run.
- Todavía queda un cuello en órdenes `delivered` antiguas/autocomplete, que debe optimizarse antes de perfiles mayores.

## Segundo Fix De Performance Aplicado Al Job Dry-Run

Hallazgo:

- `_handle_delivered` hacía una consulta por orden para detectar disputa abierta.
- Con 30 órdenes `delivered`, eso consumía 8981.533 ms en el perfil con servicios reales.

Corrección aplicada:

- `apps/api/app/modules/disputes/repository.py` ahora expone `list_open_order_ids(order_ids)`.
- `apps/api/app/modules/jobs/worker.py` precarga en lote las órdenes con disputa abierta para órdenes `delivered` vencidas.
- La regla de seguridad se conserva: una orden con disputa abierta no se autocompleta.

Validación:

- `python -m pytest apps/api/tests/test_jobs_notifications.py -q` con `PYTHONPATH=apps/api`: `7 passed, 1 warning`.
- `python -m compileall apps/api/app/modules/jobs apps/api/app/modules/disputes`: OK.

Perfil posterior con lock en memoria y servicios reales:

- Evidencia: `evidence/slice_runs/job_worker_profile_batch_disputes_20260708.json`
- processed_count: 482
- changed_count: 482
- failed_count: 0
- elapsed: 3485.068 ms
- `_handle_delivered`: 30 llamadas, 0.056 ms total.
- `disputes.list_open_order_ids`: 1 llamada, 219.647 ms.

Medición del endpoint dry-run completo:

- Evidencia: `evidence/slice_runs/job_dry_run_measure_batch_fix_20260708.json`
- Antes del fix: 157729.495 ms.
- Después del fix: 7833.285 ms.
- processed_count: 482
- failed_count: 0.

## Re-Run Funcional Completo Tras Fixes

Evidencia:

- `evidence/slice_runs/real_services_stress_initial_after_job_fix_20260708_142346.json`

Resultado:

- exit code: 0
- total requests: 37
- total errors: 0
- error rate: 0.0
- duration: 159.118 s
- p50: 3533.3018 ms
- p95: 6256.0195 ms
- p99: 14597.4205 ms
- invariant violations: todas 0

Comparación:

- Run inicial antes de fixes: 315.18 s.
- Re-run después de fixes: 159.118 s.
- `stress:jobs:dry_run` antes: 156994.8032 ms.
- `stress:jobs:dry_run` después: 6010.2419 ms.

Conclusión:

- El flujo completo pequeño sigue íntegro.
- El job dry-run ya no domina el stress.
- Todavía hay latencias de varios segundos en operaciones que tocan Supabase/Storage, pero ya no hay bloqueo de minutos.

## Run 1 - Concurrencia Pequeña

Evidencia:

- `evidence/slice_runs/real_services_concurrency_small_20260708_133407.json`

Parámetros:

- búsquedas concurrentes: 25
- requests duplicados con misma idempotency key: 8
- requests simultáneos sobre el mismo anuncio con keys distintas: 8
- órdenes únicas simultáneas: 8

Resultado:

- exit code: 0
- total requests: 49
- invariant violations: todas 0
- búsquedas: 25/25 OK
- órdenes únicas: 8/8 OK
- misma idempotency key: 8/8 devolvieron el mismo `order.id`
- mismo anuncio con distintas keys: 1 éxito y 7 `409`, correcto para evitar doble orden del mismo anuncio
- balances negativos: 0

Métricas:

- duración: 157.891 s
- throughput: 0.3103 req/s
- p50: 10531.8958 ms
- p95: 11353.4126 ms
- p99: 11363.2958 ms

Hallazgo:

- La consistencia funcionó bien, pero la latencia concurrente fue alta.

## Run 2 - Flujo Funcional Completo Pequeño

Evidencia:

- `evidence/slice_runs/real_services_stress_initial_20260708_133709.json`

Parámetros:

- profile: initial
- workflow mode: interleaved
- negocios: 2
- anuncios: 2
- órdenes: 2
- órdenes con flujo completo: 2

Resultado:

- exit code: 0
- total requests: 37
- total errors: 0
- error rate: 0.0
- invariant violations: todas 0
- double credit consumption: 0
- double credit accreditation: 0
- negative balances: 0
- invalid transitions: 0
- redis failures: 0
- db errors: 0
- timeouts: 0
- deadlocks: 0
- job lock failures: 0

Métricas:

- duración: 315.18 s
- throughput: 0.1174 req/s
- p50: 3871.7547 ms
- p95: 6758.8611 ms
- p99: 156994.8032 ms

Hallazgo fuerte:

- `stress:jobs:dry_run` tardó 156994.8032 ms.
- No falló, pero es demasiado alto para considerarlo sano sin optimización o límites más estrictos.

## Conclusión

El backend mantuvo integridad en concurrencia y flujo completo pequeño:

- idempotencia correcta
- no hubo doble orden sobre el mismo anuncio
- no hubo doble consumo de créditos
- no hubo balances negativos
- no hubo transiciones inválidas
- Redis/DB no reportaron errores

Pero no recomiendo subir a perfiles mayores todavía sin atender performance:

1. Revisar latencia de búsquedas concurrentes.
2. Revisar `expire-and-escalate-orders/dry-run`, que tardó 156s incluso en perfil pequeño.
3. Agregar cleanup controlado de datos sintéticos de stress para no ensuciar staging.
4. Luego correr profile 10 real-services y recién después considerar HTTP stress contra Railway.
