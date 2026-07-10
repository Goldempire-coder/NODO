# Architecture P0.1 Repair - Business Self-Onboarding Disabled

## Estado

PASSED_AFTER_FIX

## Problema reparado

La auditoria `architecture_cleanliness_audit_20260709.md` detecto que `POST /api/v1/businesses` todavia permitia self-onboarding legacy:

- usuario autenticado podia crear negocio directamente
- el service podia promover `remitter -> business_owner`
- esto competia con la arquitectura aprobada de Bot Registro Negocios + Admin Web + `business_access_links`

## Decision aplicada

`POST /api/v1/businesses` queda bloqueado para uso real.

Solo se permite en `APP_ENV=test` con header interno de fixture:

```txt
X-NODO-Test-Fixture: business_create
```

Ese header existe unicamente para fabricar datos en pruebas automatizadas. No es un flujo de producto, no es onboarding publico y no debe usarse en runtime real.

## Archivos modificados

- `apps/api/app/modules/businesses/routes.py`
- `apps/api/tests/test_business_verification.py`
- `apps/api/tests/test_ads_marketplace.py`
- `apps/api/tests/test_admin_console.py`
- `apps/api/tests/test_business_access_control.py`
- `apps/api/tests/test_chat_disputes.py`
- `apps/api/tests/test_business_order_ops.py`
- `apps/api/tests/test_payment_instructions_reports.py`
- `apps/api/tests/test_credits_referrals.py`
- `apps/api/tests/test_order_creation.py`
- `apps/api/tests/test_jobs_notifications.py`
- `control_plane/06_API_CONTRACTS/ERROR_CONTRACT.md`
- `control_plane/06_API_CONTRACTS/BUSINESSES_API.md`
- `control_plane/09_SLICES/slice_02_business_verification/API_CONTRACT.md`

## Evidencia de codigo

- `apps/api/app/modules/businesses/routes.py:69` bloquea el endpoint si no es test fixture.
- `apps/api/app/modules/businesses/routes.py:73` devuelve `BUSINESS_SELF_ONBOARDING_DISABLED`.
- `apps/api/tests/test_business_verification.py:160` prueba que un usuario autenticado no puede auto-crear negocio.
- `control_plane/06_API_CONTRACTS/ERROR_CONTRACT.md:41` registra el nuevo error de dominio.
- `control_plane/06_API_CONTRACTS/BUSINESSES_API.md:61` define que el endpoint no acepta creacion publica en runtime real.
- `control_plane/09_SLICES/slice_02_business_verification/API_CONTRACT.md:37` alinea el slice historico con `403 BUSINESS_SELF_ONBOARDING_DISABLED`.

## Validacion ejecutada

```txt
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_business_verification.py -q
10 passed, 1 warning

$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
132 passed, 1 warning

python -m ruff check apps\api scripts
All checks passed

python -m compileall apps\api scripts
OK

corepack pnpm --filter @nodo/web build
OK

rg -n "Creates own business|Response 201|self-onboarding publico|BUSINESS_SELF_ONBOARDING_DISABLED|POST /api/v1/businesses" ...
OK: no queda contrato activo que diga que `POST /api/v1/businesses` es self-onboarding publico.
```

## Alcance no tocado

- No cambie reglas de creditos.
- No cambie lifecycle de ordenes.
- No cambie bot intake.
- No cambie Mini App Cliente.
- No cambie Mini App Negocio.
- No cambie Admin Web.
- No hice deploy.
- No declare `READY_FOR_REAL_USE`.

## Siguiente punto recomendado

Continuar con P0.2: revisar y cerrar cualquier otro endpoint legacy que permita operar negocio sin el gate canonico `GET /api/v1/surface/session` + `business_access_links`.
