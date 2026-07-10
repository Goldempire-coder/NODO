# slice_17B_staging_guardrails_strictening_BUILDER_REPORT

## Estado final

READY_FOR_OWNER_REVIEW

## Resumen

Se endurecio exclusivamente el tooling de staging para eliminar ambiguedades antes de usar servicios reales. No se tocaron backend de producto, frontend, migraciones de producto ni deploy.

## Archivos modificados

- `scripts/staging_guardrails.py`
- `scripts/capacity_real.py`
- `apps/api/tests/test_staging_validation_tooling.py`
- `governance/builder_reports/slice_17B_staging_guardrails_strictening_BUILDER_REPORT.md`
- `evidence/slice_runs/slice_17B_staging_guardrails_strictening_evidence.md`
- `evidence/slice_runs/slice_17B_staging_guardrails_strictening_test_results.json`

## Cambios construidos

### Guardrails staging

- `NODO_ENVIRONMENT_KIND=staging` ahora es obligatorio.
- `NODO_STAGING_PROJECT_ID` ahora es obligatorio.
- `NODO_STAGING_VALIDATION=1` sigue siendo obligatorio.
- `NODO_STAGING_DB_HOST_ALLOWLIST` ahora es obligatoria y debe hacer exact-match con el host de `DATABASE_URL`.
- `NODO_STAGING_API_HOST_ALLOWLIST` ahora es obligatoria cuando hay API target y debe hacer exact-match.
- Si `SUPABASE_URL` existe, `NODO_STAGING_SUPABASE_URL` es obligatorio y debe hacer exact-match normalizado.
- `SUPABASE_URL` debe corresponder al `NODO_STAGING_PROJECT_ID`.
- `NODO_PRODUCTION_PROJECT_ID` no puede coincidir con `NODO_STAGING_PROJECT_ID`.
- Si `NODO_PRODUCTION_PROJECT_ID` aparece en targets DB/API/Supabase, se bloquea.
- Se mantiene redaccion de secretos en outputs.

### Capacity fixture modes

`scripts/capacity_real.py` ahora soporta `--fixture-mode`:

- `local_asgi`: modo local/ASGI.
- `db_seed_api_remote`: seed e invariantes por DB directa, requests medidas por API remota.
- `api_remote_only`: bloqueado por ahora porque el harness aun necesita DB directa.

Reglas nuevas:

- `--remote-base-url` sin `--fixture-mode` falla.
- `--fixture-mode api_remote_only` falla hasta que exista flujo sin DB directa.
- El JSON final incluye `fixture_mode` y `fixture_mode_detail`.

## Tests agregados/ampliados

- `NODO_ENVIRONMENT_KIND` obligatorio.
- `NODO_STAGING_PROJECT_ID` obligatorio.
- exact-match DB/API/Supabase.
- production project id bloqueado.
- `remote_base_url` sin `fixture_mode` falla.
- `db_seed_api_remote` queda identificado en output.
- `api_remote_only` bloquea cuando se requiere DB directa.
- secretos no se imprimen en outputs de smoke.

## Validaciones ejecutadas

- `python -m pytest apps\api\tests\test_staging_validation_tooling.py -q --tb=short`
  - Resultado: `15 passed, 1 warning`
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`
  - Resultado: `153 passed, 1 warning`
- `python -m ruff check apps\api scripts`
  - Resultado: `All checks passed!`
- `python -m compileall apps\api apps\web\src scripts`
  - Resultado: OK
- `corepack pnpm --filter @nodo/web build`
  - Resultado: OK

## Scan de secretos

Se ejecuto scan sobre archivos tocados y evidencias. Las coincidencias encontradas son valores sinteticos deliberados dentro de `apps/api/tests/test_staging_validation_tooling.py` y referencias historicas a comandos de scan en evidencias previas. No se imprimieron secretos reales.

## Riesgos residuales

- No se ejecutaron servicios reales por contrato.
- `api_remote_only` queda bloqueado hasta que exista fixture setup e invariantes sin DB directa.
- `db_seed_api_remote` es explicito y seguro para evidencia hibrida, pero debe tratarse como modo con acceso DB staging y cleanup obligatorio.

## Confirmaciones

- No toque backend de producto.
- No toque frontend.
- No toque migraciones de producto.
- No corri servicios reales.
- No hice deploy.
- No imprimi secretos reales.
- No declare READY_FOR_REAL_USE.
