# QA.md

## Pruebas obligatorias

- Frontend build.
- Backend pytest acumulado si se toca integracion API.
- Ruff.
- Compileall.
- Admin Web no importa `ClientWorkspace`.
- Admin Web no importa `BusinessMiniAppWorkspace`.
- Admin Web no importa shells Telegram.
- Admin Web no usa Telegram bottom nav ni Telegram MainButton como navegacion primaria.
- Admin Web bloquea `remitter` y `business_owner`.
- `support` no ve controles mutantes.
- Mutaciones admin requieren reason.
- Mutaciones admin usan `Idempotency-Key`.
- Resolucion de disputa usa contrato de slice 09.
- Compras manuales/ajustes mantienen ownership slice 08.
- No `storage_path`.
- No `account_value`.
- No secretos/tokens.
- No claims prohibidos.

## Evidencia

Builder debe guardar:

- reporte builder
- resultados de tests
- scans de imports/surface
- scans de secretos/datos sensibles
