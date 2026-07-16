# business_mini_app_usdt_trc20_payment_methods_alignment

Estado final: `READY_FOR_OWNER_REVIEW`

## Problema

La app cliente permitia seleccionar `USDT TRC20`, pero la Mini App Negocio solo exponia gestion de Zelle. Eso dejaba al negocio sin forma clara de registrar una wallet USDT TRC20 ni crear anuncios para recibir USDT.

## Cambios realizados

- Backend: `POST/PATCH/DELETE /api/v1/business/payment-methods` ahora soporta `method_type = zelle | usdt_trc20` para self-service del negocio aprobado.
- Backend: USDT TRC20 guarda `network = TRC20`, enmascara la wallet y valida formato Base58 de direccion TRON.
- Backend: las acciones siguen exigiendo negocio propio/aprobado, PIN desbloqueado e `Idempotency-Key`.
- Frontend: pantalla `Metodos de cobro` permite agregar, editar y borrar Zelle o USDT TRC20.
- Frontend: crear/editar anuncio permite seleccionar cualquier metodo activo propio, incluyendo USDT TRC20.
- Frontend: copy de negocio deja de presentar esta superficie como solo Zelle.
- Contratos: se alinearon `BUSINESS_PAYMENT_METHODS_API.md`, `B-16_PAYMENT_METHODS.md` y slice 35 a `Metodos de cobro`.

## Seguridad

- No se agregaron secretos.
- No se agrego wallet privada.
- No se movio autorizacion al frontend.
- No se expone la wallet completa en respuestas de marketplace/cliente.
- Los breadcrumbs siguen usando nombres de accion, no valores de Zelle/wallet.
- La wallet completa solo puede existir en el formulario propio del negocio cuando el usuario la esta escribiendo o editando.

## Validaciones

- `python -m pytest apps/api/tests/test_business_access_control.py apps/api/tests/test_auth_lifecycle_static.py -q --tb=short` -> `17 passed, 1 warning`
- `python -m pytest apps/api/tests -q` -> `358 passed, 1 warning`
- `python -m ruff check apps/api scripts` -> passed
- `python -m compileall apps/api apps/web/src scripts` -> passed
- `pnpm --filter @nodo/web build` usando Node de Cursor en PATH -> passed
- `git diff --check` sobre archivos tocados -> sin errores; solo warnings CRLF/LF existentes en working copy.

## Riesgos pendientes

- No se hizo deploy staging.
- No se probo manualmente dentro de Telegram despues del cambio.
- Validacion TRON implementada como formato Base58 basico; checksum completo queda como hardening futuro si se quiere mayor precision.

## Confirmaciones

- No deploy.
- No produccion.
- No infraestructura.
- No migraciones.
- No secretos.
- No wallet privada.
- No `READY_FOR_REAL_USE`.
