# BUILDER_REPORT - slice_25A_cache_consistency_hardening

## Estado final

CACHE STRATEGY READY WITH LIMITS

## Que construí

- Marketplace cache ahora degrada de forma segura cuando Redis/shared cache falla:
  - `GET /api/v1/ads/search` cae a DB como fuente.
  - No aplica fail-open a idempotency ni rate limit.
  - Registra evento operativo seguro `cache_unavailable`.
  - Registra `cache_invalidation` cuando el version bump funciona.
- `auth_user_cache` se invalida cuando admin cambia status de usuario por suspend/reactivate/block.
- Admin dashboard/metrics cache ahora usa key por rol para evitar mezcla futura de scopes.
- Tests cubren fallback Redis, invalidacion marketplace, invalidacion auth cache y key scoping admin.

## Archivos modificados

- `apps/api/app/shared/cache.py`
- `apps/api/app/modules/admin/service.py`
- `apps/api/app/modules/admin/routes.py`
- `apps/api/tests/test_ads_marketplace.py`
- `apps/api/tests/test_admin_users_business_control.py`
- `governance/builder_reports/slice_25A_cache_consistency_hardening_BUILDER_REPORT.md`
- `evidence/slice_runs/slice_25A_cache_consistency_hardening_evidence.md`
- `evidence/slice_runs/slice_25A_cache_consistency_hardening_test_results.json`

Nota: la worktree ya tenia muchos cambios previos. Este slice se limito a los archivos listados arriba.

## Riesgos corregidos

- Redis caido ya no tumba marketplace search por fallo de version/shared cache.
- Una mutacion admin de status ya no depende solo del TTL de `auth_user_cache`.
- Admin read-model cache evita una key global unica para roles distintos.
- Marketplace cache no escribe L1 local si shared cache no confirma la escritura.

## Caches que siguen prohibidas

- Credits wallet como autoridad.
- Credits ledger como autoridad.
- Order state como autoridad.
- Support visibility.
- Staff permissions para mutaciones.
- Business access links para autorizacion.
- Signed URLs.
- `storage_path`.
- `account_value`.

## Tests ejecutados

- `python -m pytest apps\api\tests\test_ads_marketplace.py::test_marketplace_search_falls_back_to_db_when_shared_cache_is_unavailable apps\api\tests\test_ads_marketplace.py::test_pause_and_archive_invalidate_marketplace_search_cache -q --tb=short`
  - Resultado: `2 passed, 1 warning`
- `python -m pytest apps\api\tests\test_admin_users_business_control.py::test_admin_user_status_change_invalidates_auth_user_cache apps\api\tests\test_admin_users_business_control.py::test_admin_read_model_cache_keys_are_role_scoped_aggregate_views -q --tb=short`
  - Resultado: `2 passed, 1 warning`
- `python -m pytest apps\api\tests\test_admin_users_business_control.py::test_admin_user_status_change_invalidates_auth_user_cache apps\api\tests\test_admin_users_business_control.py::test_admin_read_model_cache_keys_are_role_scoped_aggregate_views apps\api\tests\test_ads_marketplace.py::test_marketplace_search_falls_back_to_db_when_shared_cache_is_unavailable apps\api\tests\test_ads_marketplace.py::test_pause_and_archive_invalidate_marketplace_search_cache -q --tb=short`
  - Resultado: `4 passed, 1 warning`
- `python -m pytest apps\api\tests -q`
  - Resultado: `225 passed, 1 warning`
- `python -m ruff check apps\api scripts`
  - Resultado: `All checks passed!`
- `python -m compileall apps\api apps\web\src scripts`
  - Resultado: OK
- `corepack pnpm --filter @nodo/web build`
  - Resultado: OK

## Scans ejecutados

- `rg -n "storage_path|account_value|signed_url|access_token=|refresh_token=|BOT_TOKEN|BUSINESS_INTAKE_BOT_TOKEN|DATABASE_URL|SUPABASE_SERVICE_ROLE_KEY" apps\web\src apps\web\.next apps\web\out`
  - Resultado: sin matches.
- Mismo scan sobre archivos tocados de cache/tests:
  - Hallazgos solo en fixtures/assertions de tests existentes (`BOT_TOKEN`, `DATABASE_URL`, `account_value`, `storage_path`).
  - No hay exposicion en frontend/build.

## Riesgos residuales

- Marketplace lightweight auth sigue teniendo ventana configurada por `MARKETPLACE_READ_AUTH_CLAIM_TTL_SECONDS`; se mantiene limitado a reads public-safe.
- Si Redis cae justo despues de que un worker tenga version local cacheada, puede existir una ventana muy corta de L1 local hasta que expire el version cache; no se usa para datos financieros ni permisos.
- No se construyeron metricas/dashboards de cache. Solo logs/profiling minimo compatible con slice 24A.

## Confirmaciones

- No agregue cache nueva.
- No cachee creditos, ledger, ordenes, soporte, staff permissions, access links, signed URLs, `storage_path` ni `account_value`.
- No cambie reglas de negocio.
- No toque frontend de producto.
- No cree migraciones.
- No hice deploy.
- No declare READY_FOR_REAL_USE.
