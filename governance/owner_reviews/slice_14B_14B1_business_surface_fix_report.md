# FIX REPORT - slice_14B / 14B1 Business Mini App Surface

## Estado

`READY_FOR_OWNER_REVIEW`

Repare la deuda detectada en la auditoria de owner sobre Mini App Negocio. No toque backend, migraciones, endpoints, payloads, reglas de negocio, creditos, ordenes, auth, storage ni deploy.

## Cambios principales

### Refactor de modelo

`useBusinessMiniAppModel.ts` bajo de 676 lineas a 91 lineas y quedo como composer.

Se crearon hooks por dominio:

- `apps/web/src/hooks/business-mini-app/useBusinessAccessModel.ts`
- `apps/web/src/hooks/business-mini-app/useBusinessAdsModel.ts`
- `apps/web/src/hooks/business-mini-app/useBusinessOrdersModel.ts`
- `apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts`
- `apps/web/src/hooks/business-mini-app/useBusinessChatModel.ts`
- `apps/web/src/hooks/business-mini-app/useBusinessTelegramControls.ts`
- `apps/web/src/hooks/business-mini-app/helpers.ts`

### Refactor de pantallas

`BusinessMiniAppScreens.tsx` bajo de 513 lineas a 46 lineas y quedo como router visual.

Se crearon pantallas por dominio:

- `BusinessAccessPanel.tsx`
- `BusinessDashboardScreen.tsx`
- `BusinessAdsScreens.tsx`
- `BusinessOrdersScreens.tsx`
- `BusinessCreditsScreens.tsx`
- `BusinessChatScreen.tsx`
- `BusinessSettingsScreen.tsx`

### UI/copy corregido

- Eliminados labels internos visibles tipo `B-08_CREATE_AD`, `B-09_MY_ADS`, `B-11_INCOMING_ORDERS`, etc.
- `Ledger` se reemplazo por `Movimientos`.
- `Referrals` se reemplazo por `Referidos`.
- Se elimino copy tecnico tipo `webhook firmado` y `Checkout: URL` de la experiencia negocio.
- Enums crudos se humanizan antes de mostrarse:
  - `payment_reported` -> `Pago reportado`
  - `active` -> `Activo`
  - `paused` -> `Pausado`
  - `submitted` -> `Enviada`
- Se mantiene selector visual de metodos aprobados; no hay input manual de `payment_method_id`.
- Se mantiene sanitizacion de campos numericos para anuncios.

## Validacion ejecutada

- `corepack pnpm --filter @nodo/web build`: PASS
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: PASS, `110 passed, 1 warning`
- `python -m ruff check apps\api scripts`: PASS
- `python -m compileall apps scripts`: PASS
- Scan business app sin imports legacy cliente/admin/verificacion: PASS
- Scan business app sin IDs internos `B-0/B-1/B-2`: PASS
- Scan business app sin `storage_path`, `account_value`, secretos ni claims prohibidos: PASS

## Riesgo residual

Sigue pendiente un smoke visual estable de la Mini App Negocio con contexto Telegram simulado correctamente. El intento anterior de Playwright cayo en auth/error por dificultad de simular `initData`/SDK de Telegram en browser automation local. No bloquea este fix de codigo, pero si debe resolverse antes de declarar calidad visual final.

## Veredicto

La superficie negocio ya no queda como un bloque Frankenstein activo. Queda separada por dominio, con copy menos tecnico y sin IDs internos visibles.

No es `READY_FOR_REAL_USE`; falta smoke visual real/Telegram, deploy y servicios reales segun el plan general.
