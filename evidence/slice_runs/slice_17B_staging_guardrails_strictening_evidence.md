# slice_17B_staging_guardrails_strictening_evidence

## Estado

READY_FOR_OWNER_REVIEW

## Evidencia de endurecimiento

Archivos modificados:

- `scripts/staging_guardrails.py`
- `scripts/capacity_real.py`
- `apps/api/tests/test_staging_validation_tooling.py`

## Guardrails actualizados

El staging ya no depende de substring `prod/production` como criterio principal. Ahora requiere identidad explicita:

- `APP_ENV=staging`
- `NODO_ENVIRONMENT_KIND=staging`
- `NODO_STAGING_VALIDATION=1`
- `NODO_STAGING_PROJECT_ID`
- `NODO_STAGING_DB_HOST_ALLOWLIST`
- `NODO_STAGING_API_HOST_ALLOWLIST` cuando hay API target
- `NODO_STAGING_SUPABASE_URL` cuando hay `SUPABASE_URL`

Tambien bloquea:

- `NODO_PRODUCTION_PROJECT_ID == NODO_STAGING_PROJECT_ID`
- targets DB/API/Supabase que contengan `NODO_PRODUCTION_PROJECT_ID`
- DB/API host fuera de allowlist exacta
- `SUPABASE_URL` distinto de `NODO_STAGING_SUPABASE_URL`
- `SUPABASE_URL` que no corresponda al project id staging

## Capacity fixture modes

`capacity_real.py` ahora separa explicitamente:

- `local_asgi`
- `db_seed_api_remote`
- `api_remote_only`

`api_remote_only` esta bloqueado hasta que el harness deje de requerir DB directa. `db_seed_api_remote` reporta claramente:

- seed: `direct_db_seed`
- measured requests: `remote_api`
- invariants: `direct_db_sql`

## Validaciones ejecutadas

| Comando | Resultado |
| --- | --- |
| `python -m pytest apps\api\tests\test_staging_validation_tooling.py -q --tb=short` | `15 passed, 1 warning` |
| `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q` | `153 passed, 1 warning` |
| `python -m ruff check apps\api scripts` | `All checks passed!` |
| `python -m compileall apps\api apps\web\src scripts` | OK |
| `corepack pnpm --filter @nodo/web build` | OK |

## Scan

Comando ejecutado:

`rg -n "service-role-secret|business-secret-token|client-secret-token|password@|supabase://|token=" scripts\staging_guardrails.py scripts\capacity_real.py apps\api\tests\test_staging_validation_tooling.py governance\builder_reports evidence\slice_runs`

Resultado:

- Coincidencias en `apps/api/tests/test_staging_validation_tooling.py` son valores sinteticos de pruebas.
- Coincidencias en evidencias previas son comandos historicos de scan.
- No se encontraron secretos reales impresos por el tooling.

## Pendiente

- Ejecutar staging real queda para fase posterior con autorizacion.
- `api_remote_only` requiere una fase futura de fixture setup e invariantes via API/read-model contratado.
- No declarar READY_FOR_REAL_USE.
