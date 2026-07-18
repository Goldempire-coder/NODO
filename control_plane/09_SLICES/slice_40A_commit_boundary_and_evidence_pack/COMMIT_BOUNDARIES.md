# slice_40A_commit_boundary_and_evidence_pack

Estado: `COMMIT_BOUNDARIES_READY_FOR_OWNER_REVIEW`

Fecha: 2026-07-17

## Objetivo

Ordenar el worktree actual antes de commit/deploy. El repo contiene varias lineas de trabajo reales mezcladas; no debe enviarse todo como un unico cambio sin frontera.

## Regla

Un commit debe tener una sola razon de existir. Si dos features tocan el mismo archivo, se debe:

1. hacer staging por hunks; o
2. aceptar un paquete combinado y validarlo como tal.

No se debe hacer deploy hasta que el paquete candidato tenga evidencia propia.

## Paquete A - limpieza y estructura del repo

Proposito: evitar que estilos y artefactos locales sigan mezclados con producto.

Archivos:

- `.editorconfig`
- `apps/web/src/app/admin-web.css`
- `apps/web/src/app/globals.css`
- `apps/web/src/app/layout.tsx`
- `control_plane/09_SLICES/slice_40_repo_architecture_cleanup/REPO_ARCHITECTURE_AUDIT.md`
- `control_plane/09_SLICES/slice_40A_commit_boundary_and_evidence_pack/COMMIT_BOUNDARIES.md`

Evidencia actual:

- `pnpm --filter @nodo/web build`: PASS.
- `git diff --check`: PASS.

Riesgo:

- Bajo. No cambia reglas de negocio.

## Paquete B - admin operaciones, modo emergencia e incidentes

Proposito: que admin pueda ver estado operativo y activar/desactivar modo emergencia.

Archivos principales:

- `apps/api/app/core/errors.py`
- `apps/api/app/main.py`
- `apps/api/app/modules/admin/routes.py`
- `apps/api/app/modules/admin/service.py`
- `apps/api/app/modules/operations/`
- `apps/api/tests/test_admin_console.py`
- `apps/web/src/api/admin.ts`
- `apps/web/src/hooks/admin-web/useAdminEmergencyModeModel.ts`
- `apps/web/src/hooks/admin-web/useAdminIncidentModel.ts`
- `apps/web/src/hooks/useAdminWebModel.ts`
- `apps/web/src/screens/admin-web/AdminOverviewScreens.tsx`
- `apps/web/src/screens/admin-web/AdminWebScreens.tsx`
- `apps/web/src/types/admin.ts`
- `control_plane/09_SLICES/slice_38_admin_incident_console/`
- `database/migrations/0025_platform_emergency_mode.up.sql`
- `database/migrations/0025_platform_emergency_mode.down.sql`

Nota de frontera:

- Comparte `admin/routes.py`, `admin/service.py`, `AdminOverviewScreens.tsx`, `AdminWebScreens.tsx` y `types/admin.ts` con el paquete C. Si se quiere separar B y C, usar staging por hunks.

Riesgo:

- Medio/alto. Toca bloqueo operativo de acciones nuevas.

## Paquete C - panel UX y observabilidad frontend

Proposito: mostrar en admin donde cliente y negocio se traban, sin guardar datos sensibles.

Archivos principales:

- `apps/api/app/modules/observability/repository.py`
- `apps/api/app/modules/observability/routes.py`
- `apps/api/app/modules/observability/service.py`
- `apps/api/app/modules/admin/routes.py`
- `apps/api/app/modules/admin/service.py`
- `apps/api/tests/test_frontend_observability_ingest.py`
- `apps/api/tests/test_admin_console.py`
- `apps/web/src/observability/clientTelemetry.ts`
- `apps/web/src/hooks/admin-web/useAdminUXFrictionModel.ts`
- `apps/web/src/hooks/admin-web/useAdminDashboardMetricsModel.ts`
- `apps/web/src/hooks/admin-web/useAdminOverviewModel.ts`
- `apps/web/src/hooks/admin-web/adminOverviewTypes.ts`
- `apps/web/src/screens/admin-web/AdminOverviewScreens.tsx`
- `apps/web/src/types/admin.ts`
- `control_plane/09_SLICES/slice_39_ux_friction_panel/`
- `governance/builder_reports/slice_39_ux_friction_panel_BUILDER_REPORT.md`
- `database/migrations/0026_slice_39_frontend_observability_events.up.sql`
- `database/migrations/0026_slice_39_frontend_observability_events.down.sql`

Nota de frontera:

- Se puede combinar con paquete B si no se quiere staging por hunks, porque comparten archivos admin.

Riesgo:

- Medio. Toca observabilidad y telemetria frontend; requiere scan de redaccion.

## Paquete D - terminos vigentes y recuperacion de aceptacion cliente

Proposito: si un cliente no acepto terminos, o hay version vigente nueva, puede aceptar y continuar sin quedar bloqueado.

Archivos principales:

- `apps/api/app/auth/dependencies.py`
- `apps/api/app/modules/users/terms.py`
- `apps/api/app/modules/users/schemas.py`
- `apps/api/app/modules/users/memory_repository.py`
- `apps/api/app/modules/users/postgres_repository.py`
- `apps/api/app/routes/users.py`
- `apps/web/src/api/users.ts`
- `apps/web/src/constants/legal.ts`
- `apps/web/src/hooks/useClientWorkspaceModel.ts`
- `apps/web/src/hooks/workspace/useClientWorkspaceState.ts`
- `apps/web/src/screens/client/ClientOnboardingScreens.tsx`
- `apps/api/tests/test_auth_telegram.py`

Nota de frontera:

- Comparte rutas de orden/chat/pagos con paquete B porque algunas operaciones ahora exigen terminos y otras consultan modo emergencia. Si se separa, revisar hunks en rutas.

Riesgo:

- Medio. Toca acceso a flujos cliente.

## Paquete E - rutas protegidas por modo emergencia

Proposito: cuando admin activa modo emergencia, bloquear operaciones nuevas de riesgo sin borrar ni corromper operaciones existentes.

Archivos principales:

- `apps/api/app/modules/ads/routes.py`
- `apps/api/app/modules/credits/routes.py`
- `apps/api/app/modules/orders/remitter_routes.py`
- `apps/api/app/modules/operations/`
- `apps/api/tests/test_ads_marketplace.py`
- `apps/api/tests/test_order_creation.py`
- `apps/api/tests/test_payment_instructions_reports.py`

Nota de frontera:

- Este paquete depende del paquete B.

Riesgo:

- Alto. Debe probarse que bloquea lo nuevo sin romper consulta/seguimiento de orden existente.

## Paquete F - notificaciones/jobs visibles en incidentes

Proposito: que el centro de incidentes pueda mostrar jobs/notificaciones con problemas sin tocar jobs fuera de su alcance.

Archivos principales:

- `apps/api/app/modules/jobs/memory_repository.py`
- `apps/api/app/modules/jobs/postgres_repository.py`
- `apps/api/tests/test_jobs_notifications.py`
- `apps/api/app/modules/admin/service.py`

Nota de frontera:

- Depende del paquete B para mostrarse en admin.

Riesgo:

- Medio. Debe preservar el fix de scope: el sender Telegram solo reclama jobs inmediatos de orden.

## Paquete G - smoke cross-surface y pequenos ajustes de mini apps

Proposito: validar superficies cliente/negocio/admin con rutas actuales y headers de superficie.

Archivos principales:

- `scripts/local_surface_cross_smoke.py`
- `apps/web/src/hooks/useBusinessMiniAppModel.ts`
- `apps/web/src/hooks/useClientWorkspaceModel.ts`
- `apps/web/src/screens/client/ClientWorkspaceShell.tsx`
- `apps/api/tests/test_api_input_validation_hardening.py`
- `apps/api/tests/test_business_order_ops.py`
- `apps/api/tests/test_chat_disputes.py`
- `apps/api/tests/test_internal_staff_roles.py`
- `apps/api/tests/test_order_creation.py`
- `apps/api/tests/test_support_ticket_center.py`

Nota de frontera:

- Puede requerir combinacion con D/E si los tests dependen de terminos o emergencia.

Riesgo:

- Medio. Es evidencia y hardening, pero toca pruebas y shells.

## Recomendacion de orden

1. Paquete A.
2. Paquete B + C juntos si no se hace staging por hunks.
3. Paquete D.
4. Paquete E.
5. Paquete F.
6. Paquete G.

## Bloqueo para deploy

No desplegar hasta que el candidato exacto pase:

- `python -m pytest apps/api/tests -q`
- `python -m ruff check apps/api scripts`
- `python -m compileall apps/api apps/web/src scripts`
- `pnpm --filter @nodo/web build`
- scan sensible de `apps/web/src apps/api/app scripts`
- smoke local de superficies si el candidato toca cliente/negocio/admin

## Veredicto

`NOT_READY_FOR_DEPLOY_AS_SINGLE_MIXED_WORKTREE`

El repo esta mejor organizado, pero el worktree actual debe empaquetarse por frontera antes de commit/deploy.
