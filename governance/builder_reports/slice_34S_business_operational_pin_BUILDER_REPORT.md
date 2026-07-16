# slice_34S_business_operational_pin_BUILDER_REPORT

## Estado

`BUSINESS_OPERATIONAL_PIN_READY_FOR_OWNER_REVIEW`

## Objetivo

Agregar una capa de seguridad simple para Mini App Negocio: antes de operar acciones sensibles, el negocio debe configurar y desbloquear un PIN. El backend sigue siendo la autoridad.

## Cambios principales

- PIN por `business_access_link`, no por dispositivo.
- Hash de PIN en backend; no se guarda PIN en claro.
- Endpoints:
  - `GET /api/v1/business/security/pin`
  - `POST /api/v1/business/security/pin/setup`
  - `POST /api/v1/business/security/pin/verify`
  - `POST /api/v1/business/security/pin/lock`
- Pantalla de Mini App Negocio para crear o desbloquear PIN.
- Acciones sensibles bloqueadas si el PIN falta, esta vencido o esta bloqueado:
  - crear/editar metodos de pago propios;
  - crear/editar/pausar/reactivar/archivar/republicar anuncios;
  - compras/flujo de creditos y referidos;
  - confirmacion/rechazo/entrega de ordenes por negocio.
- Boton en Perfil para bloquear la Mini App.
- Contratos actualizados en seguridad, API, modelo de negocio y lifecycle de anuncios.

## Seguridad

- PIN permitido: 4 a 6 digitos numericos.
- Intentos fallidos incrementan contador seguro.
- Cinco intentos fallidos bloquean temporalmente el link.
- Audit events creados:
  - `business_pin_set`
  - `business_pin_verified`
  - `business_pin_failed`
  - `business_pin_locked`
- Tests verifican que el PIN no aparece en audit payloads.

## Validaciones

- `python -m pytest apps/api/tests/test_business_access_control.py apps/api/tests/test_ads_marketplace.py apps/api/tests/test_business_order_ops.py apps/api/tests/test_credits_referrals.py -q --tb=short`: `63 passed, 1 warning`
- `python -m pytest apps/api/tests -q`: `337 passed, 1 warning`
- `python -m ruff check apps/api scripts`: passed
- `python -m compileall apps/api apps/web/src scripts`: passed
- `corepack pnpm --filter @nodo/web build`: passed

## Pendientes

- No se implemento todavia agregacion/enforcement real de limite diario consumido por volumen de ordenes.
- No se hizo deploy.
- No se aplico migracion en staging/produccion.
- No se declaro `READY_FOR_REAL_USE`.

## Confirmaciones

- No se toco produccion.
- No se hizo deploy.
- No se cambio infraestructura.
- No se guardan PINs en claro.
