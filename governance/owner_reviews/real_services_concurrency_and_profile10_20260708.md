# REAL SERVICES CONCURRENCY AND PROFILE 10 ATTEMPT - 2026-07-08

## Estado

PASSED_SMALL_STEPS_WITH_PERFORMANCE_FINDINGS

No se declara READY_FOR_REAL_USE.

## Contexto

Estas pruebas corrieron desde la app local contra servicios reales de staging configurados en `.local/staging_real_services_smoke_LOCAL_ONLY.env`:

- Supabase/PostgreSQL real.
- Redis real.
- Storage adapter configurado por env de staging.
- Backend NODO ejecutado localmente por el harness de pruebas.

No fue un load test HTTP directo contra Railway.

## Run 1 - Concurrencia Mediana

Evidencia:

- `evidence/slice_runs/real_services_concurrency_medium_20260708_144416.json`

Parametros:

- Busquedas concurrentes: 75.
- Requests duplicados con la misma idempotency key: 20.
- Requests simultaneos sobre el mismo anuncio con idempotency keys distintas: 20.
- Ordenes unicas simultaneas: 18.

Resultado:

- exit_code: 0.
- total_requests: 133.
- invariant violations: todas 0.
- busquedas: 75/75 OK.
- ordenes unicas: 18/18 OK.
- misma idempotency key: 20/20 devolvieron el mismo `order.id`.
- mismo anuncio con distintas keys: 1 exito y 19 respuestas `409`, correcto para evitar doble orden sobre el mismo anuncio.
- balances negativos: 0.

Metricas:

- duracion: 250.783 s.
- throughput: 0.5303 req/s.
- p50: 27309.8948 ms.
- p95: 28509.8704 ms.
- p99: 28517.5249 ms.

Lectura:

- La integridad de concurrencia aguanto.
- Los `409` del mismo anuncio son esperados y correctos en esta prueba.
- La latencia es alta, especialmente en busquedas concurrentes contra servicios reales.

## Run 2 - Profile 10 Capado

Evidencia:

- `evidence/slice_runs/real_services_stress_profile10_cap_20260708_144844_aborted.json`

Comando intentado:

```txt
python scripts\stress_local.py --env-file .local\staging_real_services_smoke_LOCAL_ONLY.env --profile 10 --cap-businesses 5 --cap-orders 25 --workflow-mode interleaved --run-id real_services_stress_profile10_cap_20260708_144844 --output evidence\slice_runs\real_services_stress_profile10_cap_20260708_144844.json
```

Resultado:

- ABORTED_BY_OPERATOR_FOR_EXCESSIVE_INTERACTIVE_DURATION.
- Inicio: 2026-07-08 14:48:44 -04:00.
- Corte: 2026-07-08 14:59:58 -04:00.
- No produjo JSON parcial antes del corte.
- exit_code observado tras parar proceso: 1.

Lectura:

- No es un pass.
- Tampoco prueba corrupcion de datos.
- Es un hallazgo de performance/observabilidad: profile 10 capado a 5 negocios y 25 ordenes es demasiado lento o poco observable para una validacion interactiva segura contra servicios reales.

## Cambio Al Harness De Stress

Se modifico `scripts/stress_local.py` para evitar pruebas largas sin visibilidad.

Agregado:

- `--max-duration-seconds`
- `--checkpoint-output`
- checkpoints por fase
- salida final con `exit_code = 2` cuando el timeout corta la corrida

Validacion:

- `python -m compileall scripts/stress_local.py`: OK.
- `python -m ruff check scripts/stress_local.py`: OK.

## Run 3 - Profile 10 Cap 5

Evidencia:

- `evidence/slice_runs/real_services_stress_profile10_cap5_20260708_150150.json`
- `evidence/slice_runs/real_services_stress_profile10_cap5_20260708_150150.checkpoint.json`

Parametros:

- profile: 10
- cap-businesses: 3
- cap-orders: 5
- workflow-mode: interleaved
- max-duration-seconds: 480

Resultado:

- exit_code: 0.
- total_requests: 60.
- total_errors: 0.
- invariant violations: todas 0.
- businesses: 3.
- ads: 5.
- orders: 5.
- workflow_orders: 3.

Metricas:

- duracion: 277.815 s.
- throughput: 0.216 req/s.
- p50: 4067.42 ms.
- p95: 6480.8644 ms.
- p99: 10103.0166 ms.

Lectura:

- El flujo funcional pequeno contra servicios reales aguanto sin corrupcion.
- La latencia sigue en segundos por operacion.
- Los uploads de documentos/evidencia y confirmaciones son de los puntos mas pesados.

## Run 4 - Profile 10 Cap 10

Evidencia:

- `evidence/slice_runs/real_services_stress_profile10_cap10_20260708_150640.json`
- `evidence/slice_runs/real_services_stress_profile10_cap10_20260708_150640.checkpoint.json`

Parametros:

- profile: 10
- cap-businesses: 4
- cap-orders: 10
- workflow-mode: interleaved
- max-duration-seconds: 900

Resultado:

- exit_code: 0.
- total_requests: 89.
- total_errors: 0.
- invariant violations: todas 0.
- businesses: 4.
- ads: 10.
- orders: 10.
- workflow_orders: 4.

Metricas:

- duracion: 424.069 s.
- throughput: 0.2099 req/s.
- p50: 3729.7503 ms.
- p95: 8075.404 ms.
- p99: 10812.8462 ms.

Lectura:

- Segundo escalon paso limpio en integridad.
- La performance sigue siendo el bloqueo principal para subir volumen.
- Operaciones con storage real y confirmacion/ledger estan en rango de varios segundos.

## Run 5 - Profile 10 Cap 25

Evidencia:

- `evidence/slice_runs/real_services_stress_profile10_cap25_retry_20260708_155103.json`
- `evidence/slice_runs/real_services_stress_profile10_cap25_retry_20260708_155103.checkpoint.json`

Nota previa:

- El primer intento `real_services_stress_profile10_cap25_20260708_154508` fallo por `STORAGE_UNAVAILABLE` durante upload de documento de negocio.
- Se verifico Supabase Storage con upload directo exitoso y se limpio el run parcial.
- El retry se ejecuto desde base limpia para este run.

Parametros:

- profile: 10
- cap-businesses: 5
- cap-orders: 25
- workflow-mode: interleaved
- max-duration-seconds: 1500

Resultado:

- exit_code: 0.
- total_requests: 149.
- total_errors: 0.
- invariant violations: todas 0.
- businesses: 5.
- ads: 25.
- orders: 25.
- workflow_orders: 5.

Metricas:

- duracion: 795.956 s.
- throughput: 0.1872 req/s.
- p50: 4959.1455 ms.
- p95: 7029.0417 ms.
- p99: 10416.2439 ms.

Limpieza:

- `evidence/slice_runs/cleanup_execute_real_services_stress_profile10_cap25_retry_20260708_155103.json`
- `evidence/slice_runs/cleanup_postcheck_real_services_stress_profile10_cap25_retry_20260708_155103.json`
- Postcheck: 0 sessions, 0 businesses, 0 ads, 0 orders, 0 payment_reports, 0 file_assets para este run.
- Users sinteticos y audit_logs quedan retenidos por diseno append-only.

Lectura:

- El flujo cap 25 paso sin corrupcion ni errores funcionales despues del retry.
- Hay una senal real de fragilidad/intermitencia en storage durante carga de documentos.
- La performance sigue lenta: p95 de ~7.0 s y p99 de ~10.4 s.

## Conclusiones

Lo bueno:

- La concurrencia mediana no rompio idempotencia.
- No hubo doble orden sobre el mismo anuncio.
- No hubo balances negativos.
- No hubo violaciones de invariantes en el run mediano.
- Profile 10 cap 5, cap 10 y cap 25 pasaron con 0 errores y 0 invariantes rotas.
- La limpieza controlada por `run_id` funciono y dejo las filas de producto del cap 25 en 0.

Lo que falta antes de subir volumen:

- Mantener y expandir los timeouts/checkpoints agregados al stress harness.
- Perfilar busquedas concurrentes y creacion de ordenes con Supabase real.
- Investigar la intermitencia de Supabase Storage observada en el primer intento cap 25.
- Optimizar endpoints lentos antes de saltar a pruebas de 50/100+ ordenes.

## Recomendacion

No subir todavia a 200-1000 clientes.

El siguiente paso correcto es performance profiling:

- medir latencia por endpoint/fase en stress real,
- identificar si el cuello principal esta en storage, Supabase DB, audit writes, uploads o queries,
- corregir los puntos lentos,
- y solo despues repetir con `cap-orders 50`.
