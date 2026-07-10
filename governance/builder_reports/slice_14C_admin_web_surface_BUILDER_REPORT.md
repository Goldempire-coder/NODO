# BUILDER_REPORT - slice_14C_admin_web_surface

## Estado final

READY_FOR_OWNER_REVIEW

## Resumen

Se construyo la superficie Admin Web como entrada desktop separada mediante `?surface=admin`. El Admin Web queda fuera del shell Telegram: no usa `AppRoot`, Telegram MainButton, `themeParams` ni bottom nav. La Mini App Cliente y la Mini App Negocio no fueron reconstruidas.

## Archivos creados/modificados

- `apps/web/src/hooks/useAdminWebModel.ts`
- `apps/web/src/screens/admin-web/AdminWebWorkspace.tsx`
- `apps/web/src/screens/admin-web/AdminWebShell.tsx`
- `apps/web/src/screens/admin-web/AdminWebScreens.tsx`
- `apps/web/src/screens/auth/AuthEntryPage.tsx`
- `apps/web/src/app/globals.css`
- `governance/builder_reports/slice_14C_admin_web_surface_BUILDER_REPORT.md`
- `evidence/slice_runs/slice_14C_admin_web_surface_evidence.md`
- `evidence/slice_runs/slice_14C_admin_web_surface_test_results.json`

## Que construi

- Superficie Admin Web desktop-first con sidebar, top bar, tablas, filtros, busqueda, paneles de detalle y estados loading/empty/error/forbidden.
- Modelo admin aislado en `useAdminWebModel`.
- Entrada tecnica separada por `?surface=admin`.
- Vistas para dashboard, metricas, negocios, ordenes, disputas, audit logs, credit purchases, ajustes manuales, jobs, intake y soporte read-only/placeholder gobernado.
- Confirmacion visual para mutaciones criticas con `reason` e `Idempotency-Key`.
- Uso de endpoints admin existentes sin cambiar contratos ni backend.

## Que NO construi

- No construi Mini App Cliente.
- No construi Mini App Negocio.
- No construi Bot Registro Negocios.
- No hice deploy.
- No agregue dependencias.
- No cambie reglas de creditos, ordenes, anuncios, disputas ni pagos.
- No declare `READY_FOR_REAL_USE`.

## Endpoints reutilizados

- `GET /api/v1/admin/dashboard`
- `GET /api/v1/admin/metrics`
- `GET /api/v1/admin/businesses`
- `GET /api/v1/admin/businesses/pending`
- `GET /api/v1/admin/businesses/{id}`
- `POST /api/v1/admin/businesses/{id}/approve`
- `POST /api/v1/admin/businesses/{id}/reject`
- `POST /api/v1/admin/businesses/{id}/verification-documents/{file_id}/view-url`
- `GET /api/v1/admin/orders`
- `GET /api/v1/admin/orders/{id}`
- `GET /api/v1/admin/disputes`
- `GET /api/v1/admin/disputes/{id}`
- `POST /api/v1/admin/disputes/{id}/resolve`
- `GET /api/v1/admin/audit-logs`
- `GET /api/v1/admin/credit-purchases`
- `POST /api/v1/admin/credit-purchases/{id}/approve`
- `POST /api/v1/admin/credit-purchases/{id}/reject`
- `POST /api/v1/admin/credits/adjust`
- `GET /api/v1/admin/jobs/runs`
- `POST /api/v1/admin/jobs/expire-and-escalate-orders/dry-run`

## Validaciones ejecutadas

- `corepack pnpm --filter @nodo/web build` - OK.
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q` - OK, `105 passed, 1 warning in 13.77s`.
- `python -m ruff check apps\api scripts` - OK, `All checks passed!`.
- `python -m compileall apps scripts` - OK.
- Scan Admin Web contra imports prohibidos - OK, sin coincidencias.
- Scan Admin Web contra reglas Telegram activas - OK, sin coincidencias.
- Scan frontend source/build contra secretos, `storage_path` y claims prohibidos - OK, sin coincidencias.
- Scan Admin Web/build contra `account_value` - OK, sin coincidencias.

## Runner 14C

No existe runner especifico `slice_14C` en `scripts`. Se dejo evidencia equivalente con build frontend, pytest acumulado, ruff, compileall y scans obligatorios.

## Riesgos residuales

- La entrada Admin Web queda por ahora como superficie tecnica `?surface=admin`; dominio/ruta final y deploy quedan fuera de este slice.
- La validacion visual fue por build y estructura/CSS, no por screenshot browser automatizado.
- Sigue sin ser `READY_FOR_REAL_USE`.

## Confirmaciones

- No modifique backend.
- No modifique migraciones.
- No instale dependencias.
- No hice deploy.
- No avance a Bot Registro Negocios.
- No cambie reglas de producto.
- No declare `READY_FOR_REAL_USE`.
