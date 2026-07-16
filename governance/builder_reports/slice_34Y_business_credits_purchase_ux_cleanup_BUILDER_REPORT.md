# slice_34Y_business_credits_purchase_ux_cleanup

Estado final: `READY_FOR_OWNER_REVIEW`

## Objetivo

Pulir el flujo de compra de creditos Base USDC en la Mini App Negocio para que sea mas claro, menos ruidoso y mas seguro para operar.

## Cambios realizados

- La pantalla principal de creditos queda enfocada en balance y `Comprar`.
- Se quito el boton `Referidos` del dashboard de creditos; referidos sigue disponible desde Perfil.
- Se normalizo el texto de red como `Base`.
- Al crear una compra nueva se limpia cualquier tx hash escrito previamente.
- La pantalla de pago pendiente muestra pasos cortos:
  - red Base
  - monto exacto
  - pegar tx hash
- La wallet destino y el monto exacto tienen acciones de copiar visibles.
- El boton de copiar wallet muestra feedback visual y texto `Copiado`.
- Si el pago queda acreditado al verificar tx hash, se refresca el wallet de creditos en el modelo frontend.

## Fuera de alcance

- No se cambio la verificacion on-chain.
- No se acredita solo por pegar tx hash.
- No se cambio pricing de paquetes.
- No se agregaron wallets privadas ni firmas.
- No se hizo deploy.
- No se toco produccion.

## Riesgos pendientes

- Falta prueba manual dentro de Telegram real despues de deploy.
- La pantalla de referidos todavia requiere una decision de producto sobre si se mantiene, se simplifica o se oculta temporalmente.
- El estado final de acreditacion sigue dependiendo del verificador backend y del RPC configurado.

## Validacion ejecutada

- `python -m pytest apps/api/tests/test_credits_referrals.py::test_base_usdc_business_buy_screen_hides_legacy_fallback_controls apps/api/tests/test_auth_lifecycle_static.py -q --tb=short` -> `8 passed, 1 warning`
- `python -m pytest apps/api/tests -q` -> `352 passed, 1 warning`
- `python -m ruff check apps/api scripts` -> passed
- `python -m compileall apps/api apps/web/src scripts` -> passed
- `pnpm --filter @nodo/web build` con Node runtime bundled -> passed
- `git diff --check` -> passed con warnings existentes de CRLF/LF
