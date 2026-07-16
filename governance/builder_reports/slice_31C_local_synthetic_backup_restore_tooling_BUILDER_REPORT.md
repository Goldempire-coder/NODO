# BUILDER_REPORT - slice_31C_local_synthetic_backup_restore_tooling

Estado final: LOCAL_SYNTHETIC_BACKUP_RESTORE_VALIDATED

Modo: BUILD_TOOLING_ONLY

## Alcance construido

- Tooling local/sintetico para seed -> backup/dump -> restore local -> integrity validation.
- Script: `scripts/local_synthetic_backup_restore.py`.
- Tests locales del tooling en `apps/api/tests/test_hardening_local.py`.
- Evidencia de corrida local en `evidence/slice_runs/slice_31C_local_synthetic_backup_restore_test_results.json`.

## Guardrails implementados

- Requiere `APP_ENV=local`.
- Reusa el guardrail local existente de URL de DB.
- Rechaza `run_id` con referencias a production/staging/provider.
- Crea solo bases generadas con prefijo `nodo_31c_`.
- Usa solo el contenedor local `nodo_postgres_local` por defecto.
- Usa `pg_dump`, `pg_restore` y `psql` dentro del contenedor local de Postgres.
- No toca Supabase, staging, produccion ni providers.
- Limpia por defecto solo las DBs generadas.
- No escribe secretos ni connection strings en el JSON de evidencia.

## Drill local ejecutado

Comando:

```powershell
python scripts\local_synthetic_backup_restore.py --env-file .env.local.example --run-id slice31c_local_001 --output evidence\slice_runs\slice_31C_local_synthetic_backup_restore_test_results.json
```

Resultado:

- `pg_dump`: PostgreSQL 16.14, OK.
- `pg_restore`: PostgreSQL 16.14, OK.
- `psql`: PostgreSQL 16.14, OK.
- Migraciones aplicadas: 20.
- Dump generado: `.local\backup_restore\slice31c_local_001\source.dump`.
- Dump size: 176204 bytes.
- Source schema: 32 tables, 186 indexes, 555 constraints.
- Restored schema: 32 tables, 186 indexes, 555 constraints.
- Count mismatches: 0.
- Failures: 0.
- Generated DB cleanup: enabled.

## Datos sinteticos cubiertos

- users
- businesses
- business_access_links
- business_payment_methods
- ads
- orders
- order_state_events
- credit_wallets
- credits_ledger
- credit_purchases
- support_tickets
- support_messages
- support_ticket_events
- staff_profiles
- staff_permissions
- audit_logs
- notification_jobs
- business_intake_requests

## Validaciones ejecutadas

```powershell
python -m pytest apps\api\tests\test_hardening_local.py -q --tb=short
python -m ruff check scripts\local_synthetic_backup_restore.py apps\api\tests\test_hardening_local.py
python -m compileall scripts\local_synthetic_backup_restore.py apps\api\tests\test_hardening_local.py
python -m ruff check apps\api scripts
python -m compileall apps\api apps\web\src scripts
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
corepack pnpm --filter @nodo/web build
rg -n -i "<sensitive token/url/path/value patterns>" evidence\slice_runs\slice_31C_local_synthetic_backup_restore_test_results.json
```

Resultados:

- Pytest especifico: 10 passed.
- Ruff especifico: All checks passed.
- Compileall especifico: OK.
- Ruff general: All checks passed.
- Compileall general: OK.
- Pytest acumulado: 260 passed, 1 warning.
- Frontend build: OK.
- Scan evidencia JSON: 0 matches.

## Qué NO se hizo

- No Supabase real.
- No staging.
- No produccion.
- No datos reales.
- No deploy.
- No cambios backend/frontend/migraciones.
- No restore real provider.
- No `READY_FOR_REAL_USE`.

## Riesgos residuales

- Esto valida solo restore local/sintetico.
- No valida backups provider.
- No valida Supabase Storage real.
- No valida secrets recovery provider.
- No valida performance/costo de restore real.
- La siguiente fase debe ser 31D staging/isolated con aprobacion explicita.
