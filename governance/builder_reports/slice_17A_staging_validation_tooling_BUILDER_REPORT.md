# slice_17A_staging_validation_tooling_BUILDER_REPORT

## Estado final

READY_FOR_OWNER_REVIEW

## Resumen

Se construyo tooling seguro para preparar validacion staging real sin ejecutar servicios reales, sin deploy y sin tocar producto. El slice agrega guardrails reutilizables para env staging, migraciones staging con ledger/lock, validacion de schema staging, smoke de Supabase Storage, smoke seguro de Telegram webhook, cleanup staging por `run_id` y extiende `capacity_real.py` para que `--remote-base-url` aplique a escenarios no-marketplace.

## Archivos modificados

- `scripts/staging_guardrails.py`
- `scripts/apply_staging_migrations.py`
- `scripts/validate_staging_schema.py`
- `scripts/staging_storage_smoke.py`
- `scripts/staging_telegram_webhook_smoke.py`
- `scripts/staging_cleanup_synthetic_run.py`
- `scripts/capacity_real.py`
- `apps/api/tests/test_staging_validation_tooling.py`
- `governance/builder_reports/slice_17A_staging_validation_tooling_BUILDER_REPORT.md`
- `evidence/slice_runs/slice_17A_staging_validation_tooling_evidence.md`
- `evidence/slice_runs/slice_17A_staging_validation_tooling_test_results.json`

## Scripts creados

- `staging_guardrails.py`: carga env-file explicito, exige `APP_ENV=staging`, `NODO_STAGING_VALIDATION=1`, allowlists DB/API, confirmacion para acciones mutantes y redaccion de secretos.
- `apply_staging_migrations.py`: plan/dry-run por defecto, apply explicito, ledger `nodo_schema_migrations`, checksum SHA-256, advisory lock y output JSON.
- `validate_staging_schema.py`: reutiliza checks de schema existentes con guardrails staging y output JSON.
- `staging_storage_smoke.py`: upload privado sintetico, signed URL corta, download/checksum y delete cleanup sin persistir `storage_path` ni signed URL.
- `staging_telegram_webhook_smoke.py`: reject-only por defecto con secret invalido; valid test-chat opcional sin imprimir token/secret.
- `staging_cleanup_synthetic_run.py`: wrapper staging seguro sobre cleanup por `run_id`, dry-run default y apply explicito con confirmacion.

## Cambios en harness

- `scripts/capacity_real.py` ahora usa un cliente HTTP comun para marketplace, order-create, same-ad race, duplicate idempotency, payment confirm y mixed.
- Cuando `--remote-base-url` esta presente, las solicitudes medidas usan ese target remoto.
- El resultado del harness incluye bloque `cleanup` con `run_id` y comando recomendado.

## Migraciones

No se crearon migraciones de producto. El ledger de staging se crea por el script de tooling solo cuando se ejecute `apply_staging_migrations.py --apply` con guardrails staging.

## Validaciones ejecutadas

- `python -m pytest apps\api\tests\test_staging_validation_tooling.py -q --tb=short`
  - Resultado: `8 passed, 1 warning`
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`
  - Resultado: `146 passed, 1 warning`
- `python -m ruff check apps\api scripts`
  - Resultado: `All checks passed!`
- `python -m compileall apps\api apps\web\src scripts`
  - Resultado: OK
- `corepack pnpm --filter @nodo/web build`
  - Resultado: OK
- Scan frontend/source/build:
  - Comando: `rg -n "SUPABASE_SERVICE_ROLE_KEY|BOT_TOKEN|JWT_SECRET|JWT_REFRESH_SECRET|storage_path|account_value|escrow|fondos protegidos|pago garantizado|garantía de entrega|garantia de entrega|NODO recibió dinero" apps\web\src apps\web\.next apps\web\out`
  - Resultado: sin coincidencias

## Tests nuevos

- staging permitido y secretos redactados
- production rechazado
- mutaciones requieren confirmacion
- migration plan no aplica sin `--apply`
- cleanup dry-run no ejecuta deletes
- `capacity_real.py` usa cliente remoto en escenarios no-marketplace
- storage smoke no persiste `storage_path` ni signed URL
- telegram smoke no imprime token ni secret

## Riesgos residuales

- No se ejecutaron servicios reales por contrato del slice.
- La ejecucion real de migraciones, storage, Telegram y capacity queda pendiente para una fase staging autorizada.
- El fixture setup de `capacity_real.py` sigue preparando dataset internamente antes de medir rutas remotas; esto mantiene invariantes actuales, pero la fase real debe documentar si se acepta `db_seed` o se exige setup remoto completo.
- El cleanup de objetos Supabase Storage del smoke se implementa para el objeto sintetico del propio smoke; cleanup completo de objetos generados por otros flujos staging debe ejecutarse con `run_id` y evidencia dedicada.

## Confirmaciones

- No modifique backend de producto.
- No modifique frontend.
- No modifique migraciones existentes.
- No corri servicios reales.
- No use DB real.
- No hice deploy.
- No imprimi secretos.
- No cambie reglas de negocio.
- No declare READY_FOR_REAL_USE.
