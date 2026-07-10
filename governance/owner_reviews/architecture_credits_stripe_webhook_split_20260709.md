# Architecture Review - Credits Stripe Webhook Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica de verificacion/parsing del webhook Stripe fuera de `CreditService`.

No se cambiaron reglas de negocio, endpoints, payloads, frontend, migraciones, contratos, storage, servicios reales ni deploy.

## Archivos modificados

- `apps/api/app/modules/credits/stripe_webhook.py`
- `apps/api/app/modules/credits/service.py`

## Cambio realizado

- Se creo `parse_stripe_webhook_event`.
- La verificacion HMAC, tolerancia de timestamp y parseo JSON del evento Stripe salieron de `CreditService`.
- `CreditService.stripe_webhook` conserva el flujo de credito, auditoria y respuesta.
- Errores conservados:
  - `STRIPE_SIGNATURE_INVALID`
  - `VALIDATION_ERROR`

## Medicion despues del corte

- `service.py`: 320 lineas
- `stripe_webhook.py`: 39 lineas

Referencia de mejora:

- `service.py` estaba en 345 lineas antes del corte.

## Validacion ejecutada

- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_credits_referrals.py -q`
  - Resultado: `7 passed, 1 warning`
- `python -m ruff check apps\api\app\modules\credits apps\api\tests\test_credits_referrals.py`
  - Resultado: `All checks passed`
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`
  - Resultado: `133 passed, 1 warning`
- `python -m ruff check apps\api scripts`
  - Resultado: `All checks passed`
- `python -m compileall apps\api scripts`
  - Resultado: OK
- `corepack pnpm --filter @nodo/web build`
  - Resultado: OK

## Resultado arquitectonico

La capa de servicio de creditos ya no contiene logica criptografica/protocolo de Stripe. Esa responsabilidad queda aislada en `stripe_webhook.py`, mientras `CreditService` queda enfocado en aplicar la decision de negocio del evento ya validado.

## Riesgo residual

`CreditService` todavia mezcla casos de uso de negocio, admin, compras, referrals y webhook handling. Siguiente lectura recomendada: dividir admin actions (`admin_list_purchases`, `admin_approve_purchase`, `admin_reject_purchase`, `admin_adjust`) en una unidad separada si el corte conserva la interfaz publica y reduce complejidad real.
