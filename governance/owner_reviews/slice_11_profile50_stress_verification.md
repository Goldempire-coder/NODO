# slice_11_profile50_stress_verification

## Estado final

PASSED_AFTER_FIXES

El perfil 50 local fue ejecutado contra Docker Postgres/Redis local, sin servicios reales, sin deploy y sin declarar `READY_FOR_REAL_USE`.

## Run id

`profile50_owner_run_20260704211809`

## Evidencia generada

- `evidence/slice_runs/slice_11_profile50_migrations.json`
- `evidence/slice_runs/slice_11_profile50_schema_validation.json`
- `evidence/slice_runs/slice_11_local_stress_profile50.json`
- `evidence/slice_runs/slice_11_local_stress_profile50.log`
- `evidence/slice_runs/slice_11_local_stress_profile50_failed_session_expired.log`
- `evidence/slice_runs/slice_11_profile50_post_schema_validation.json`
- `evidence/slice_runs/slice_11_hardening_deploy_test_results.json`
- `evidence/slice_runs/slice_11_profile50_run_id.txt`

## Infraestructura local

- `docker compose -f docker-compose.local.yml up -d`: ejecutado antes del stress.
- `python scripts\local_infra_check.py --env-file .env.local.example --require-services`: OK.
- Docker: `Docker version 29.3.1, build c2be9cc`.
- Docker Compose: `Docker Compose version v5.1.0`.
- Postgres local: `127.0.0.1:55432` OK.
- Redis local: `127.0.0.1:56379` OK.

No se usaron Supabase real, Redis cloud, storage real, Stripe live, Telegram real ni deploy.

## Migraciones y schema

### Migraciones

Comando:

```powershell
python scripts\apply_local_migrations.py --env-file .env.local.example --reset --output evidence\slice_runs\slice_11_profile50_migrations.json
```

Resultado:

- `reset`: `true`
- migraciones aplicadas: `0001` a `0011`
- failures: `[]`
- exit_code: `0`

### Schema pre-stress

Comando:

```powershell
python scripts\validate_local_schema.py --env-file .env.local.example --output evidence\slice_runs\slice_11_profile50_schema_validation.json
```

Resultado:

- tables: `23`
- indexes: `128`
- Redis ping: `true`
- failures: `[]`
- exit_code: `0`

### Schema post-stress

Comando:

```powershell
python scripts\validate_local_schema.py --env-file .env.local.example --output evidence\slice_runs\slice_11_profile50_post_schema_validation.json
```

Resultado:

- tables: `23`
- indexes: `128`
- Redis ping: `true`
- failures: `[]`
- exit_code: `0`

## Target del perfil 50

Target efectivo emitido por `scripts/stress_local.py`:

- businesses: `100`
- orders: `1000`
- marketplace_searches: `1000`
- stripe_events: `100`
- manual_reviews: `100`

Actual ejecutado:

- businesses: `100`
- ads: `1000`
- orders: `1000`
- workflow_orders: `100`
- steps_recorded: `4506`

Nota: `PROFILE_TARGETS` define `stripe_events=250` para perfil 50, pero el harness reduce el target efectivo a `min(stripe_events, businesses) = 100`. El stress actual no ejecuta Stripe/manual review como flujo independiente; queda registrado como riesgo residual del harness, no como fallo del run ejecutado.

## Resultado stress profile 50

Comando:

```powershell
python scripts\stress_local.py --env-file .env.local.example --profile 50 --run-id profile50_owner_run_20260704211809 --output evidence\slice_runs\slice_11_local_stress_profile50.json
```

Resultado del JSON:

- exit_code: `0`
- total_requests: `4405`
- total_errors: `0`
- error_rate: `0.0`
- duration_seconds: `1045.592`
- throughput_per_second: `4.2129`
- p50_ms: `188.5068`
- p95_ms: `396.8092`
- p99_ms: `572.732`

Nota de consola: PowerShell/Codex reporto exit code `1` por `StarletteDeprecationWarning` emitido a stderr al importar `fastapi.testclient`. El JSON generado por el harness cerro con `exit_code=0`, sin errores y sin violaciones. Ese warning ya estaba aceptado temporalmente por owner.

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

Log scan:

- `SESSION_EXPIRED`: no encontrado en el run final.
- `Traceback`: no encontrado en el run final.
- `RuntimeError`: no encontrado en el run final.
- HTTP `401`, `429`, `5xx`: no encontrados en el run final.

## Bug encontrado y fix aplicado

### Hallazgo

Primer intento de profile 50 fallo en:

```txt
stress:orders:create:908 failed: 401 SESSION_EXPIRED
```

Run fallido inicial:

- run_id: `profile50_owner_run_20260704210027`
- evidencia preservada: `evidence/slice_runs/slice_11_local_stress_profile50_failed_session_expired.log`

Clasificacion: bug de harness local. El backend mantiene correctamente access token corto (`ACCESS_TOKEN_TTL_SECONDS=900`); el harness reutilizaba el access token inicial durante una corrida mas larga que el TTL.

### Fix aplicado

Archivo modificado:

- `scripts/local_smoke.py`

Lineas relevantes:

- `scripts/local_smoke.py:41`: margen local de refresh.
- `scripts/local_smoke.py:62-86`: `stamp_login` y `ensure_fresh_login`.
- `scripts/local_smoke.py:88-100`: `headers` y `bearer` refrescan antes de devolver Authorization.
- `scripts/local_smoke.py:103-110`: `login` guarda timestamp monotonic de emision.

Regla preservada: no se cambio el TTL del backend ni la politica de auth; se uso el endpoint contratado `/api/v1/auth/refresh`.

Evidencia del fix ejercitado: el run final contiene requests `POST /api/v1/auth/refresh` con `200 OK` durante workflows de confirmacion, y no contiene `SESSION_EXPIRED`.

## Pruebas ejecutadas

### Runner slice 11

Comando:

```powershell
python scripts\run_slice_11_tests.py
```

Resultado: exit code `0`.

Resumen de checks:

- `pytest apps/api/tests/test_hardening_local.py -q`: `7 passed in 0.14s`
- `scripts/local_infra_check.py --env-file .env.local.example`: exit_code `0`
- `scripts/validate_local_schema.py --env-file .env.local.example`: exit_code `0`
- `scripts/concurrency_local.py --env-file .env.local.example --searches 10 --duplicate-requests 5 --unique-orders 5`: exit_code `0`
- `corepack.cmd pnpm --filter @nodo/web build`: exit_code `0`
- `python -m ruff check apps/api scripts`: exit_code `0`
- `python -m compileall apps/api scripts`: exit_code `0`
- frontend secret/private-data/scope scan: exit_code `0`

### Pytest acumulado

Comando:

```powershell
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
```

Resultado:

- `92 passed, 1 warning in 16.91s`
- warning: `StarletteDeprecationWarning` de `fastapi.testclient`.

### Ruff

Comando:

```powershell
python -m ruff check apps\api scripts
```

Resultado:

- `All checks passed!`
- exit code `0`

### Compileall

Comando:

```powershell
python -m compileall apps scripts
```

Resultado:

- exit code `0`
- Nota: el comando enumero tambien `apps/web/node_modules`, por estar bajo `apps`, pero no fallo.

## Riesgos residuales

- No es `READY_FOR_REAL_USE`.
- No se ejecuto profile 100.
- No se uso Supabase real, Redis cloud, storage real, Stripe live, Telegram real ni deploy.
- El warning Starlette/httpx sigue aceptado temporalmente.
- `scripts/stress_local.py` reduce `stripe_events` efectivo a `100` en profile 50 y no ejecuta Stripe/manual review como flujo independiente; conviene cerrarlo antes de usar el harness como medicion amplia de credit purchases.
- La prueba es local/secuencial con TestClient; no reemplaza prueba de concurrencia real, deploy, smoke Telegram real ni hardening con servicios reales.

## Recomendacion

Avanzar a profile 100 local solo como siguiente stress local gobernado.

No avanzar a produccion ni declarar `READY_FOR_REAL_USE`.
