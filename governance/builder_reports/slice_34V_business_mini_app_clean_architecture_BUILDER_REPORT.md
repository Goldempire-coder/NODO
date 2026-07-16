# slice_34V_business_mini_app_clean_architecture

Estado final: `READY_FOR_OWNER_REVIEW`

## Objetivo

Reducir acoplamiento en la Mini App Negocio sin cambiar reglas financieras, endpoints, migraciones, infraestructura ni deploy.

## Cambios implementados

- `apps/web/src/hooks/business-mini-app/useBusinessHomeSummaryModel.ts`
  - Extrae la carga del Home fuera de `useBusinessMiniAppModel`.
  - Centraliza el refresh coordinado de wallet, anuncios y ordenes.
  - Maneja estados `idle`, `loading`, `ready` y `error` del resumen.

- `apps/web/src/hooks/useBusinessMiniAppModel.ts`
  - Deja de contener la logica de refresh del Home.
  - Queda como ensamblador de modulos: acceso, creditos, anuncios, ordenes, chat, soporte y controles de Telegram.

- `apps/web/src/hooks/business-mini-app/businessPinGuards.ts`
  - Centraliza codigos, mensajes y routing de errores de PIN.
  - Evita duplicar checks de `BUSINESS_PIN_NOT_SET`, `BUSINESS_PIN_REQUIRED` y `BUSINESS_PIN_LOCKED`.

- `apps/web/src/hooks/business-mini-app/useBusinessAccessModel.ts`
  - Usa `businessPinGuards` para acciones sensibles de Zelle.

- `apps/web/src/hooks/business-mini-app/useBusinessAdsModel.ts`
  - Usa `businessPinGuards` para crear, editar, pausar, reactivar, borrar y republicar anuncios.

- `apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts`
  - Usa `businessPinGuards` para compra de creditos Base USDC.

- `apps/api/tests/test_auth_lifecycle_static.py`
  - Protege que el Home no vuelva a vivir en el hook principal.
  - Protege que los mensajes/guards de PIN tengan una fuente comun.

## Que NO se toco

- No se modificaron reglas de creditos.
- No se modificaron reglas de anuncios.
- No se modificaron endpoints.
- No se modificaron migraciones.
- No se modifico infraestructura.
- No se hizo deploy.
- No se tocaron secretos, wallets privadas ni RPC keys.

## Validacion ejecutada

- `python -m pytest apps/api/tests/test_auth_lifecycle_static.py -q --tb=short` -> `7 passed`
- `python -m pytest apps/api/tests -q` -> `352 passed, 1 warning`
- `python -m ruff check apps/api scripts` -> passed
- `python -m compileall apps/api apps/web/src scripts` -> passed
- `pnpm --filter @nodo/web build` con runtime Node empaquetado -> passed
- `git diff --check` -> passed, solo avisos de CRLF/LF

## Riesgos pendientes

- No se hizo walkthrough manual dentro de Telegram despues de esta limpieza.
- Aun quedan pantallas grandes, especialmente `BusinessAdsScreens.tsx`, que deben dividirse en componentes mas pequenos en un slice posterior.
- Este slice no resuelve problemas provider/deploy ni configuracion de Railway/Cloudflare.

## Veredicto

`READY_FOR_OWNER_REVIEW`
