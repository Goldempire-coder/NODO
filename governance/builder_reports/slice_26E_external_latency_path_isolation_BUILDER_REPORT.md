# BUILDER_REPORT - slice_26E_external_latency_path_isolation

Estado final: EXTERNAL_LATENCY_SOURCE_IDENTIFIED

## Que construí

- Agregué `scripts/external_latency_probe.py`, un runner seguro de staging para aislar latencia externa de marketplace sin tocar producto.
- El runner soporta:
  - `--client-mode shared`
  - `--client-mode new-per-request`
  - `--max-connections`
  - `--concurrency`
  - `--requests`
  - `--profile-marketplace`
  - guardrails staging existentes con `--env-file`
  - output JSON redacted.
- El runner captura por request:
  - `external_duration_ms`
  - `X-NODO-Process-Time-Ms`
  - delta external/backend
  - `Server-Timing`
  - `X-Request-Id`
  - `X-Correlation-Id`
  - `X-NODO-Operation-Id`
  - status/error
  - response bytes
  - presencia de `_profile`.
- Agregué tests unitarios en `apps/api/tests/test_staging_validation_tooling.py`.

## Que NO construí

- No cambié backend de producto.
- No cambié frontend de producto.
- No cambié DB, migraciones, queries, cache productiva ni reglas de negocio.
- No cambié Railway/Supabase/Upstash/Cloudflare.
- No hice deploy.
- No declaré `READY_FOR_REAL_USE`.

## Archivos modificados

- `scripts/external_latency_probe.py`
- `apps/api/tests/test_staging_validation_tooling.py`

## Evidencia staging ejecutada

Se ejecutaron corridas read-only contra staging usando `.local/staging_validation_17C_LOCAL_ONLY.env` y guardrails:

| Run | Modo | Requests | Concurrency | Max connections | Status | External p95 | Backend p95 | Delta p95 |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| serial shared | shared | 20 | 1 | 1 | 20x 200 | 224.5941 ms | 12.5951 ms | 222.4664 ms |
| c50 shared | shared | 400 | 50 | 50 | 400x 200 | 1565.5765 ms | 15.9535 ms | 1563.4487 ms |
| c50 new-per-request | new-per-request | 400 | 50 | 50 | 399x 200, 1x 599 | 26926.6521 ms | 58.4591 ms | 26917.0087 ms |
| c50 shared conn10 | shared | 400 | 50 | 10 | 400x 200 | 5609.0034 ms | 10.4355 ms | 5603.2654 ms |

Resumen generado:

- `evidence/slice_runs/slice_26E_summary.json`

## Clasificación

Principal: `HARNESS_CLIENT_CONNECTION_OVERHEAD`

Secundaria: `CLIENT_CONNECTION_POOL_LIMIT`

La evidencia concreta:

- `new-per-request` fue 17.1992x peor en p95 externo que `shared` c50 y produjo un `ConnectTimeout`.
- Limitar el pool compartido a 10 conexiones fue 3.5827x peor que usar 50 conexiones.
- En el mejor comparativo c50 compartido, backend p95 quedó en 15.9535 ms mientras external p95 quedó en 1565.5765 ms.
- DB acquire p95 y query p95 no explican la latencia externa.
- Auth p95 y cache p95 tampoco explican el delta dominante.

## Validaciones ejecutadas

- `python -m pytest apps\api\tests\test_staging_validation_tooling.py -q --tb=short`
  - Resultado: 40 passed, 1 warning.
- `python -m pytest apps\api\tests -q`
  - Resultado: 237 passed, 1 warning.
- `python -m ruff check apps\api scripts`
  - Resultado: All checks passed.
- `python -m compileall apps\api apps\web\src scripts`
  - Resultado: OK.
- `corepack pnpm --filter @nodo/web build`
  - Resultado: OK.
- Scan evidencia/script:
  - Resultado: solo `DATABASE_URL` y `REDIS_URL` con valor `[REDACTED]`; no secretos reales encontrados.

## Riesgos residuales

- La URL staging permitida por guardrails contiene el hostname `nodo-api-production.up.railway.app`; no se trató como producción porque el env local la marca como staging y la allowlist exacta la permite, pero el nombre puede confundir futuras auditorías.
- El primer serial shared tuvo un outlier frío de ~15.7 s externo; conviene separar warm-up explícito si se busca comparar p95 operativo estable.
- `new-per-request` no debe usarse para medición normal de capacidad porque fuerza overhead artificial de conexión/cliente.

## Próximo paso recomendado

No subir infraestructura todavía. Repetir medición de capacidad usando cliente compartido con pool suficiente, y si se quiere aislar red/edge real, crear un slice separado para ejecutar el mismo probe desde una ubicación cercana a Railway o desde un runner controlado fuera de la máquina local.

Confirmación: no deploy, no producción, no infraestructura cambiada, no `READY_FOR_REAL_USE`.
