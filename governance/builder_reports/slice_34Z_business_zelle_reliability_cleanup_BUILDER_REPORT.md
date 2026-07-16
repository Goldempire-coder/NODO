# slice_34Z_business_zelle_reliability_cleanup

Estado: DEPLOYED_TO_STAGING_OWNER_REVIEW_REQUIRED

## Objetivo
Hacer confiable la gestion de Zelle en la Mini App Negocio: agregar, editar y borrar deben tener estados claros, no deben depender de una lista cacheada y no deben dejar anuncios pegados a un Zelle borrado sin una ruta visible de recuperacion.

## Alcance
- Frontend Mini App Negocio.
- Cliente API de metodos de pago del negocio.
- Tests estaticos y tests backend ya existentes de ownership/delete/reactivacion.

## Fuera de alcance
- No produccion.
- No migraciones.
- No cambios de reglas financieras.
- No cambios en wallet, RPC ni verificador on-chain.
- No cambios de ownership backend.

## Cambios
- `apps/web/src/api/businesses.ts`: la lectura de Zelle usa `cache: "no-store"` y cache buster para evitar respuestas viejas despues de borrar.
- `apps/web/src/hooks/business-mini-app/useBusinessAccessModel.ts`: filtra metodos inactivos, limpia `payment_method_id` si ya no quedan Zelle activos, y agrega `startPaymentMethodCreate` para que Nuevo Zelle sea una accion real.
- `apps/web/src/screens/business-app/BusinessAdsScreens.tsx`: el borrado de Zelle ahora requiere un segundo toque visible con `Confirmar borrar`, muestra estados por fila y evita boton ambiguo de conteo.
- `apps/web/src/app/globals.css`: estilos para contador de Zelle y confirmacion de borrado.
- `apps/api/tests/test_auth_lifecycle_static.py`: cobertura estatica para no-store, filtro de activos, confirmacion de borrado y accion Nuevo Zelle.
- `evidence/slice_runs/slice_34Z_staging_deploy_evidence.md`: evidencia de deploy staging sin secretos.

## Validacion ejecutada
- `python -m pytest apps/api/tests/test_auth_lifecycle_static.py apps/api/tests/test_ads_marketplace.py::test_approved_business_can_delete_own_zelle_payment_method_from_active_list apps/api/tests/test_ads_marketplace.py::test_business_ads_show_inactive_zelle_details_and_block_reactivation apps/api/tests/test_ads_marketplace.py::test_paused_ad_with_deleted_zelle_can_move_to_active_zelle_before_reactivation apps/api/tests/test_ads_marketplace.py::test_business_cannot_update_or_delete_another_business_zelle -q --tb=short` -> 11 passed, 1 warning.
- `python -m pytest apps/api/tests -q` -> 352 passed, 1 warning.
- `python -m ruff check apps/api scripts` -> passed.
- `python -m compileall apps/api apps/web/src scripts` -> passed.
- `pnpm --filter @nodo/web build` con runtime Node local -> passed.
- `git diff --check` -> passed con avisos CRLF/LF existentes.
- Scan limitado de archivos tocados -> sin secretos reales; solo nombres de campos esperados en tests/payloads.
- Build web con `NEXT_PUBLIC_API_BASE_URL=https://nodo-api-production.up.railway.app` y `NEXT_PUBLIC_APP_URL=https://nodo-staging.pages.dev` -> passed.
- Cloudflare Pages deploy production branch `staging` -> `https://78ba1c95.nodo-staging.pages.dev`.
- Stable web URL `https://nodo-staging.pages.dev/business/` -> HTTP 200.
- Railway `TELEGRAM_WEB_APP_URL` actualizado a `https://nodo-staging.pages.dev`.
- Railway `/health`, `/ready`, `/version` -> OK despues del cambio.

## Pendiente
- Prueba manual en Telegram Mini App real pendiente.

## Riesgo
Bajo. El cambio no altera el backend financiero ni el contrato de autorizacion. Refuerza el cliente contra datos obsoletos y mejora UX de acciones sensibles.

## Rollback
Revertir los cambios de los archivos listados en este reporte. No hay migraciones ni cambios de datos que revertir.
