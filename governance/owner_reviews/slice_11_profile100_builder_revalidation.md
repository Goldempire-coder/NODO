# slice_11 profile 100 builder revalidation

## Estado final

PASSED

No READY_FOR_REAL_USE. No se conectaron servicios reales, no se hizo deploy y no se avanzó a setup de servicios reales.

## Run id

`profile100_builder_revalidation_20260704221709`

## Archivos de evidencia generados

- `evidence/slice_runs/slice_11_profile100_revalidation_run_id.txt`
- `evidence/slice_runs/slice_11_profile100_revalidation_migrations.json`
- `evidence/slice_runs/slice_11_profile100_revalidation_schema_pre.json`
- `evidence/slice_runs/slice_11_local_stress_profile100_revalidation.json`
- `evidence/slice_runs/slice_11_local_stress_profile100_revalidation.log`
- `evidence/slice_runs/slice_11_profile100_revalidation_schema_post.json`
- `evidence/slice_runs/slice_11_hardening_deploy_test_results.json`

## Target exacto del profile 100

Target efectivo registrado por `stress_local.py`:

```json
{
  "businesses": 200,
  "orders": 2000,
  "marketplace_searches": 2000,
  "stripe_events": 200,
  "manual_reviews": 200
}
```

Actual ejecutado:

```json
{
  "businesses": 200,
  "ads": 2000,
  "orders": 2000,
  "workflow_orders": 200
}
```

Nota: `scripts/stress_local.py` define profile 100 con `stripe_events = 500`, pero el harness lo limita efectivamente a `min(stripe_events, businesses)`, por eso la evidencia registra `stripe_events = 200`.

## Resultado del stress

- Total requests: 8805
- Total errors: 0
- Error rate: 0.0
- Duration: 1175.596 seconds
- Throughput: 7.4898 requests/second
- p50: 92.9981 ms
- p95: 175.7869 ms
- p99: 298.5364 ms
- `stress_local.py` JSON exit_code: 0

El proceso PowerShell reportó exit code 1 por `StarletteDeprecationWarning` emitido en stderr por `fastapi.testclient`. El JSON de salida del harness quedó completo, válido y con `exit_code: 0`; el warning Starlette/httpx ya está aceptado temporalmente como riesgo residual.

## Invariant violations

```json
{
  "idempotency_duplicates": 0,
  "idempotency_replay_conflicts": 0,
  "double_credit_consumption": 0,
  "double_credit_accreditation": 0,
  "negative_balances": 0,
  "invalid_transitions": 0,
  "redis_failures": 0,
  "db_errors": 0,
  "timeouts": 0,
  "deadlocks": 0,
  "job_lock_failures": 0
}
```

## Schema validation

Pre-stress:

- Archivo: `evidence/slice_runs/slice_11_profile100_revalidation_schema_pre.json`
- Exit code: 0
- Tables: 23
- Indexes: 128
- Redis ping: true
- Failures: []

Post-stress:

- Archivo: `evidence/slice_runs/slice_11_profile100_revalidation_schema_post.json`
- Exit code: 0
- Tables: 23
- Indexes: 128
- Redis ping: true
- Failures: []

## Log scan obligatorio

Escaneo de `evidence/slice_runs/slice_11_local_stress_profile100_revalidation.log` para:

- `Address already in use`
- `OperationalError`
- `SESSION_EXPIRED`
- `RATE_LIMITED`
- `Traceback`
- `RuntimeError`
- `HTTP/1.1 500`
- `HTTP/1.1 5`
- `HTTP/1.1 401`
- `HTTP/1.1 429`

Resultado: sin hits.

## Bugs encontrados y fixes aplicados

No se encontraron bugs nuevos en esta revalidacion.

No se modifico backend, frontend, migraciones, contratos ni reglas de producto durante esta revalidacion.

## Pruebas ejecutadas

- `docker compose -f docker-compose.local.yml up -d`: OK; `nodo_postgres_local` y `nodo_redis_local` running.
- `python scripts\local_infra_check.py --env-file .env.local.example --require-services`: exit_code 0.
- `python scripts\apply_local_migrations.py --env-file .env.local.example --reset --output evidence\slice_runs\slice_11_profile100_revalidation_migrations.json`: exit_code 0, 11 migraciones aplicadas, failures [].
- `python scripts\validate_local_schema.py --env-file .env.local.example --output evidence\slice_runs\slice_11_profile100_revalidation_schema_pre.json`: exit_code 0.
- `python scripts\stress_local.py --env-file .env.local.example --profile 100 --run-id profile100_builder_revalidation_20260704221709 --output evidence\slice_runs\slice_11_local_stress_profile100_revalidation.json`: JSON exit_code 0.
- `python scripts\validate_local_schema.py --env-file .env.local.example --output evidence\slice_runs\slice_11_profile100_revalidation_schema_post.json`: exit_code 0.
- `python scripts\run_slice_11_tests.py`: exit_code 0.
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: 92 passed, 1 warning.
- `python -m ruff check apps\api scripts`: All checks passed.
- `python -m compileall apps scripts`: exit_code 0.
- `corepack pnpm --filter @nodo/web build`: exit_code 0.
- Frontend source/build scan for secrets/private terms: OK, no forbidden terms found.

## Riesgos residuales

- No se ejecutaron Supabase cloud, Redis cloud, storage real, Stripe live, Telegram real ni deploy.
- El warning Starlette/httpx de `fastapi.testclient` sigue presente y aceptado temporalmente.
- El profile 100 valida stress local con Docker Postgres/Redis, no readiness de servicios reales.
- `stripe_events` efectivo queda limitado por el harness a 200 aunque el perfil base declare 500.

## Recomendacion

Avanzar a setup controlado de servicios reales cuando el owner lo autorice, manteniendo claro que esto no implica `READY_FOR_REAL_USE`.
