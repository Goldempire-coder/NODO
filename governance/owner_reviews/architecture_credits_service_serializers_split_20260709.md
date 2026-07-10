# Architecture Review - Credits Service Serializers Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica de serializadores publicos del servicio de creditos.

No se cambiaron reglas de wallet, ledger, compras, Stripe, pagos manuales, referrals, admin adjustments, permisos, idempotencia, audit events, endpoints, payloads, frontend, migraciones, contratos ni servicios reales.

## Archivos modificados

- `apps/api/app/modules/credits/serializers.py`
- `apps/api/app/modules/credits/service.py`

## Cambio realizado

- Se creo `serializers.py` para centralizar:
  - `purchase_public`
  - `file_public`
  - `ledger_public`
  - `referral_public`
  - `mask_tail`
- `CreditService` conserva los casos de uso:
  - wallet
  - ledger
  - Stripe checkout/webhook
  - pago manual
  - referrals
  - admin approve/reject/adjust
- El masking de referencia manual y hash se mantiene solo en vista admin.

## Medicion despues del corte

- `apps/api/app/modules/credits/service.py`: 345 lineas
- `apps/api/app/modules/credits/serializers.py`: 80 lineas

Antes del corte, `service.py` tenia 412 lineas.

## Validacion ejecutada

- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q -k "credit or credits"`: 18 passed, 115 deselected, 1 warning
- `python -m ruff check apps\api\app\modules\credits apps\api\tests`: PASS
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: 133 passed, 1 warning
- `python -m ruff check apps\api scripts`: PASS
- `python -m compileall apps\api scripts`: PASS
- `corepack pnpm --filter @nodo/web build`: PASS

## Riesgo residual

`apps/api/app/modules/credits/postgres_repository.py` sigue siendo el archivo de mayor riesgo en creditos con 491 lineas. Mezcla wallet, compras, aprobacion, referral bonus, ajustes admin y referral codes/eventos.

## Siguiente corte recomendado

Leer primero el bloque `approve_purchase` y `_grant_referral_bonus_if_eligible_pg` en `credits/postgres_repository.py`. El corte mas probable es mover la logica de referral bonus a un helper transaccional propio sin cambiar la transaccion de aprobacion.
