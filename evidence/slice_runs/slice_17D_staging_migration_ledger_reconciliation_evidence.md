# Evidence - slice_17D_staging_migration_ledger_reconciliation

## Scope

Tooling local seguro para reconciliar el ledger de migraciones staging. No se tocaron servicios reales.

## Implementacion

- Se agrego `scripts/reconcile_staging_migration_ledger.py`.
- Se agregaron pruebas al archivo existente `apps/api/tests/test_staging_validation_tooling.py`.
- Fix owner-audit: `notification_jobs` ahora verifica `notification_type` y `scheduled_for`, no `job_type` ni `scheduled_at`.
- `orders_active_created_idx` queda como check requerido porque pertenece a `0016_query_performance_indexes.up.sql`.

## Comportamiento verificado por tests

- El reconciliador exige la constraint `ads_credit_hold_ledger_fk`.
- El reconciliador exige columnas e indices criticos.
- El reconciliador usa los nombres canonicos de columnas de `notification_jobs`.
- El plan bloquea checksum mismatch.
- El plan marca filas de ledger pendientes cuando el schema esta verificado.
- El modo dry-run no llama a apply.
- El modo apply requiere confirmacion staging.

## Validaciones

```text
python -m pytest apps\api\tests\test_staging_validation_tooling.py -q --tb=short
22 passed, 1 warning
```

```text
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
160 passed, 1 warning
```

```text
python -m ruff check apps\api scripts
All checks passed!
```

```text
python -m compileall apps\api apps\web\src scripts
OK
```

```text
corepack pnpm --filter @nodo/web build
OK
```

## No real services

- No se ejecuto apply real.
- No se uso DB real.
- No se uso Redis real.
- No se uso Storage real.
- No se hizo deploy.
- No se imprimieron secretos.
