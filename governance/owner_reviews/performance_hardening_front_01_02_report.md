# Performance Hardening - Fronts 01 and 02

## Estado

PASSED_LOCAL_VALIDATION

## Front 01 - Indices

Se agrego migracion reversible:

- `database/migrations/0016_query_performance_indexes.up.sql`
- `database/migrations/0016_query_performance_indexes.down.sql`

Objetivo: reducir escaneos costosos en listados, busquedas, colas admin, intake, jobs y consultas recientes.

Validacion local:

- Apply up inicial: OK
- Rollback down: OK
- Apply up final: OK
- Schema local final: 25 tablas, 154 indices, Redis ping OK

Evidencia:

- `evidence/slice_runs/0016_query_performance_indexes_up_first.json`
- `evidence/slice_runs/0016_query_performance_indexes_down.json`
- `evidence/slice_runs/0016_query_performance_indexes_up_final.json`
- `evidence/slice_runs/0016_pre_reapply_schema.json`
- `evidence/slice_runs/0016_post_schema.json`

## Front 02 - Cache quirurgico

Se agrego cache TTL corto solo para read models admin:

- `GET /api/v1/admin/dashboard`
- `GET /api/v1/admin/metrics`

Archivos tocados:

- `apps/api/app/core/config.py`
- `apps/api/app/main.py`
- `apps/api/app/modules/admin/routes.py`
- `apps/api/app/modules/admin/service.py`
- `apps/api/tests/test_admin_console.py`

Reglas preservadas:

- No se cacheo auth.
- No se cacheo business access.
- No se cachearon mutaciones.
- No se cambio RBAC.
- No se cambio masking.
- Cada vista admin sigue auditando aunque el read model venga de cache.

## Validacion ejecutada

- `python -m pytest apps\api\tests\test_admin_console.py -q`: 8 passed, 1 warning
- `python -m pytest apps\api\tests -q`: 134 passed, 1 warning
- `python -m ruff check apps\api scripts`: OK
- `python -m compileall apps\api apps\web\src scripts`: OK
- `corepack pnpm --filter @nodo/web build`: OK

## Pendiente recomendado

- Repetir stress local despues de aplicar `0016` sobre base limpia.
- Medir p95/p99 antes/despues en flujos marketplace, admin dashboard, orders, intake bot.
- Si los numeros lo justifican, pasar a cache distribuido Redis para lecturas publicas o admin, manteniendo TTL corto e invalidacion controlada.
- Revisar queries con evidencia real de Supabase/Postgres antes de agregar mas indices.

## Estado real

No es `READY_FOR_REAL_USE`.

Siguen pendientes servicios reales, smoke Telegram real, deploy real y pruebas con trafico real/controlado.
