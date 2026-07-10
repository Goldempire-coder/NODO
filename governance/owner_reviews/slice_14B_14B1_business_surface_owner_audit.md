# OWNER AUDIT - slice_14B / 14B1 Business Mini App Surface

## Estado

`PASSED_FOR_SURFACE_SECURITY`

`NEEDS_UI_AND_CODE_POLISH_BEFORE_EXPANDING_BUSINESS_APP`

No hice cambios de producto. Esta auditoria revisa si lo construido por builder quedo gobernado, separado y sin señales de Frankenstein.

## Evidencia revisada

- `apps/web/src/screens/business-app/BusinessMiniAppWorkspace.tsx`
- `apps/web/src/screens/business-app/BusinessMiniAppShell.tsx`
- `apps/web/src/screens/business-app/BusinessMiniAppScreens.tsx`
- `apps/web/src/hooks/useBusinessMiniAppModel.ts`
- `apps/web/src/constants/businessViews.ts`
- `apps/web/src/types/domain.ts`
- `apps/web/src/lib/numericInput.ts`

Tambien se intento smoke visual con Playwright sobre:

- `output/playwright/business-dashboard.png`

La captura cayo en pantalla de auth/error porque el harness local no logro simular completamente el contexto Telegram Mini App para `auth/telegram`. Eso no prueba fallo en Telegram real, pero si deja pendiente un smoke visual controlado para `?surface=business`.

## Lo que esta bien

1. La Mini App Negocio ya esta separada de cliente/admin en el render activo.
   - No aparecen imports activos de `ClientWorkspace`, `RemitterScreens`, `AdminConsoleScreens` ni `VerificationScreens` dentro de `screens/business-app` o `useBusinessMiniAppModel`.

2. El gate de acceso negocio ya usa backend.
   - `useBusinessMiniAppModel.ts` llama `GET /api/v1/surface/session`.
   - Envia `X-NODO-Surface: business_mini_app`.
   - No usa `/api/v1/businesses/me` como gate principal.

3. Crear anuncio ya no pide un UUID manual.
   - `BusinessMiniAppScreens.tsx` usa selector visual para `payment_method_id`.

4. No vi leaks directos en la superficie negocio.
   - Busqueda de `storage_path`, `account_value`, secretos y claims prohibidos no encontro hits en business-app/model.

5. Inputs numericos del negocio estan sanitizados en frontend.
   - Tasa, monto minimo y monto maximo usan `sanitizeDecimalInput`, `inputMode="decimal"` y `pattern`.

## Hallazgos que no me gustan

### 1. Pantallas negocio muestran IDs internos al usuario

En `BusinessMiniAppScreens.tsx` hay labels visibles como:

- `B-08_CREATE_AD`
- `B-09_MY_ADS`
- `B-10_ARCHIVED_ADS`
- `B-16_PAYMENT_METHODS`
- `B-11_INCOMING_ORDERS`
- `B-12_BUSINESS_ORDER_DETAIL`
- `B-13_BUSINESS_CHAT`
- `B-04_BUSINESS_DASHBOARD`
- `B-05_BUY_CREDITS`
- `B-06_CREDIT_PAYMENT_PENDING`
- `B-07_MY_CREDITS_LEDGER`
- `B-15_REFERRAL_PROGRAM`
- `B-17_BUSINESS_SETTINGS`

Esto es el hallazgo mas importante de UI. Es codigo interno filtrado al producto. Hace que la app se sienta generica/prototipo.

### 2. Hay copy tecnico para usuarios negocio

Ejemplos encontrados:

- `Ledger`
- `Referrals`
- `Stripe acredita solo con webhook firmado`
- `Checkout: {url}`
- estados como `payment_reported`, `active`, `paused`, `submitted` pueden terminar visibles

Debe cambiarse a lenguaje humano:

- `Movimientos`
- `Referidos`
- `Pago con tarjeta iniciado`
- `Completa el pago en la ventana segura`
- `Pago reportado`, `Activo`, `Pausado`, `En revision`

### 3. El codigo ya esta separado, pero todavia no esta suficientemente pequeno

Conteo actual:

- `useBusinessMiniAppModel.ts`: 676 lineas
- `BusinessMiniAppScreens.tsx`: 513 lineas
- `BusinessMiniAppShell.tsx`: 162 lineas
- `BusinessMiniAppWorkspace.tsx`: 10 lineas

Esto no es el Frankenstein original, pero si es una mini concentracion de logica. Antes de seguir agregando negocio/soporte/bot, debe dividirse.

Division recomendada:

- `useBusinessAccessModel`
- `useBusinessAdsModel`
- `useBusinessOrdersModel`
- `useBusinessCreditsModel`
- `useBusinessChatModel`
- `useBusinessTelegramControls`
- `BusinessDashboardScreen`
- `BusinessAdsScreens`
- `BusinessOrdersScreens`
- `BusinessCreditsScreens`
- `BusinessSettingsScreen`

### 4. Sigue existiendo un tipo global mezclado

`types/domain.ts` mantiene `BusinessView` con vistas de cliente, negocio y admin en el mismo union type.

Aunque la business app usa allowlist y no renderiza cliente/admin, esto es deuda estructural. Para que no vuelva el Frankenstein, conviene separar:

- `ClientView`
- `BusinessMiniAppView`
- `AdminWebView`

### 5. Queda codigo legacy mixto en repo

No esta activo en la business app nueva, pero sigue existiendo:

- `BusinessOperationsScreens.tsx`
- `WorkspaceShell.tsx`
- `useBusinessWorkspaceModel.ts`
- `useCreditsReferralsModel.ts` con mezcla de negocio/admin

No hay que borrarlo a ciegas, pero si marcarlo como legacy o ir apagandolo cuando 14A/14B/14C queden estables.

### 6. Falta smoke visual estable de negocio

La captura local cayo en auth/error:

`http://127.0.0.1:3014/api/v1/auth/telegram`

Esto ocurre por dificultad de simular Telegram initData en browser automation. Necesitamos un smoke gobernado para surface business, con initData firmado o harness dedicado, para ver pantallas reales antes de aprobar visualmente.

## Veredicto

El builder si siguio la instruccion grande:

- separo superficie negocio,
- puso gate backend,
- no dejo negocio dentro de cliente,
- no dejo admin dentro de negocio,
- elimino input manual inseguro de payment method.

Pero no aprobaria el resultado como acabado visual/profesional todavia.

Debe venir una fase corta de pulido/refactor negocio antes de construir mas encima.

## Prompt recomendado siguiente

Trabaja en `C:\Users\carlo\Documents\Playground\NODO`.

MODO: FIX_ONLY sobre `slice_14B_business_mini_app_surface` y `slice_14B1_business_access_control_contracts`.

Objetivo: reparar deuda UI/codigo detectada por owner audit sin cambiar reglas de negocio, endpoints, payloads, backend, migraciones, auth, creditos, ordenes ni contratos.

Debes:

1. Quitar de la UI negocio todos los IDs internos visibles tipo `B-08_CREATE_AD`, `B-09_MY_ADS`, etc.
2. Reemplazar copy tecnico por copy humano y consistente:
   - `Ledger` -> `Movimientos`
   - `Referrals` -> `Referidos`
   - no mostrar `Checkout: URL`
   - no mostrar `webhook firmado` al usuario
   - no mostrar enums crudos como `payment_reported`, `active`, `paused`, `submitted`
3. Dividir `BusinessMiniAppScreens.tsx` en componentes pequenos por dominio.
4. Dividir `useBusinessMiniAppModel.ts` en hooks pequenos por dominio, manteniendo `useBusinessMiniAppModel` solo como composer.
5. No importar cliente/admin dentro de business app.
6. No reintroducir `BusinessOperationsScreens`, `WorkspaceShell`, `AdminConsoleScreens`, `VerificationScreens` ni `RemitterScreens`.
7. Mantener `GET /api/v1/surface/session` como gate canonico con `X-NODO-Surface: business_mini_app`.
8. Mantener selector visual de payment methods; no input manual de `payment_method_id`.
9. Mantener sanitizacion numerica.
10. Crear o ajustar smoke visual/harness para poder capturar pantallas negocio sin depender fragilmente de Telegram real.

Validacion obligatoria:

- `corepack pnpm --filter @nodo/web build`
- `python -m pytest apps\api\tests -q`
- `python -m ruff check apps\api scripts`
- `python -m compileall apps scripts`
- scan: business app sin imports cliente/admin/verificacion legacy
- scan: sin `B-0`, `B-1` visibles en `screens/business-app`
- scan: sin `storage_path`, `account_value`, secretos ni claims prohibidos
- evidencia visual de dashboard, anuncios, crear anuncio, ordenes, detalle orden y creditos

Estado esperado si pasa:

`READY_FOR_OWNER_REVIEW`

