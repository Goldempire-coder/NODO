# slice_39_ux_friction_panel

Estado final: `READY_FOR_OWNER_REVIEW`

## Resumen

Se construyo un panel Admin `UX` para identificar donde cliente y negocio se traban mas dentro de las Mini Apps.

El panel usa eventos frontend observability seguros y agregados. No guarda IP, wallet completa, Zelle completo, PIN, tokens, comprobantes ni signed URLs.

## Cambios principales

- Persistencia segura de eventos frontend en `frontend_observability_events`.
- Repositorio in-memory y Postgres para eventos UX.
- Endpoint admin `GET /api/v1/admin/ux-friction`.
- Pantalla Admin `UX` con:
  - friccion por superficie;
  - pantallas con mas friccion;
  - acciones con problemas;
  - errores API visibles al usuario;
  - recomendaciones.
- Envio frontend gated por flags:
  - `OBSERVABILITY_INGEST_ENABLED=1`
  - `NEXT_PUBLIC_OBSERVABILITY_INGEST_ENABLED=1`

## Archivos clave

- `apps/api/app/modules/observability/repository.py`
- `apps/api/app/modules/observability/service.py`
- `apps/api/app/modules/admin/service.py`
- `apps/api/app/modules/admin/routes.py`
- `apps/web/src/observability/clientTelemetry.ts`
- `apps/web/src/screens/admin-web/AdminOverviewScreens.tsx`
- `apps/web/src/hooks/admin-web/useAdminUXFrictionModel.ts`
- `database/migrations/0026_slice_39_frontend_observability_events.up.sql`
- `database/migrations/0026_slice_39_frontend_observability_events.down.sql`

## Validacion

- `python -m pytest apps/api/tests/test_frontend_observability_ingest.py apps/api/tests/test_admin_console.py -q --tb=short`: `18 passed`
- `python -m pytest apps/api/tests -q`: `375 passed, 1 warning`
- `python -m ruff check apps/api scripts`: passed
- `python -m compileall apps/api apps/web/src scripts`: passed
- `pnpm --filter @nodo/web build`: passed

## Scan de sensibilidad

El scan encontro solo valores falsos dentro de tests y nombres de campos usados para redaccion (`wallet`, `zelle`, `signed_url`, `mnemonic`, etc.). No se encontraron secretos reales introducidos por el slice.

## Riesgos pendientes

- El panel acumula eventos nuevos solo si los flags de observabilidad estan activos en backend y frontend.
- No se hizo deploy.
- No se probo en Telegram Mini App real.
- No se declaro `READY_FOR_REAL_USE`.
