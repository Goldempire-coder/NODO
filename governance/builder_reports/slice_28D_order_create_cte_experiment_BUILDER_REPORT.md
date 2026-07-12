# slice_28D_order_create_cte_experiment - BUILDER_REPORT

Estado final: REJECTED_AND_ROLLED_BACK

## Resumen

Se probó una optimización quirúrgica para `POST /api/v1/orders`: combinar el `update ads -> in_order` y el `insert orders` en una sola sentencia SQL con CTE.

El cambio fue seguro funcionalmente en pruebas locales, pero la medición cloud c100 mostró regresión clara en tiempo interno backend de creación de órdenes. Por eso el cambio fue revertido y staging fue redesplegado con build rollback.

## Cambio probado

- Archivo: `apps/api/app/modules/orders/postgres_create_order.py`
- Idea: reemplazar dos operaciones SQL separadas dentro de la transacción por una sola operación `with moved_ad as (...) insert into orders ... select ... from moved_ad`.
- Objetivo: reducir ida/vuelta a Postgres en el hot path de creación de órdenes.

## Validaciones locales del experimento

- `python -m pytest apps\api\tests\test_order_creation.py -q --tb=short`: `15 passed, 1 warning`
- `python -m pytest apps\api\tests -q`: `258 passed, 1 warning`
- `python -m ruff check apps\api scripts`: OK
- `python -m compileall apps\api apps\web\src scripts`: OK
- `corepack pnpm --filter @nodo/web build`: OK

## Medición staging

Build experimental desplegado:

- `staging-28d-20260711204421`

Corridas cloud desde GitHub Actions:

- c50: `29174473665`
- c100: `29174774724`

Comparación contra 28C2:

| Escenario | 28C2 order backend p95 | 28D order backend p95 | Resultado |
|---|---:|---:|---|
| c50 | 456.6227 ms | 440.2408 ms | mejora menor |
| c100 | 282.6614 ms | 594.5846 ms | regresión fuerte |

Aunque el p95 visto por cliente mejoró en c100, esa métrica está afectada por variabilidad externa de runner/red. Para este cambio, la métrica decisiva era el tiempo interno del backend, y ahí el experimento empeoró c100.

## Decisión

El cambio fue rechazado y revertido. No queda diff de código de 28D.

Build rollback desplegado:

- `staging-28d-rollback-20260711210924`

## Cleanup

Se ejecutó cleanup staging para:

- `gha_mixed50_slice28d_fixture_20260711204719`
- `gha_mixed100_slice28d_fixture_20260711205704`

Verificación posterior:

- negocios: `0`
- anuncios: `0`
- órdenes: `0`

Audit logs y usuarios sintéticos se retuvieron por diseño append-only.

## Artefactos

- `evidence/slice_runs/slice_28D_cloud_comparison_summary.json`
- `evidence/slice_runs/slice_28D_cleanup_verification.json`
- `evidence/slice_runs/slice_28D_final_version_check.json`
- `evidence/slice_runs/slice_28D_order_create_cte_experiment_evidence.md`
- `evidence/slice_runs/slice_28D_order_create_cte_experiment_test_results.json`

## Riesgo residual

El siguiente cuello no debe atacarse con CTE de move+insert. La ruta actual 28C2 sigue siendo mejor para c100 backend. Próximo análisis recomendado: reducir costo de `auth:get_user_by_id` solo si se mantiene seguridad fuerte, o medir más granularmente transaction/audit/context con profiles disponibles en el runner.

Confirmación: no se declaró `READY_FOR_REAL_USE`.
