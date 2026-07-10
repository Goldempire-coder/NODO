# Architecture Review - Credits Business Referrals Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica de referrals de negocio fuera de `CreditService`.

No se cambiaron reglas de negocio, endpoints, payloads, frontend, migraciones, contratos, storage, servicios reales ni deploy.

## Archivos modificados

- `apps/api/app/modules/credits/business_referrals.py`
- `apps/api/app/modules/credits/service.py`

## Cambio realizado

- Se creo `CreditBusinessReferrals`.
- `CreditService` conserva sus metodos publicos y delega:
  - `referrals`
  - `apply_referral`
- La creacion/lectura de referral code, calculo de earned credits, aplicacion de codigo, idempotencia y audit de referral quedaron agrupados en `business_referrals.py`.
- La interfaz de rutas no cambio.

## Medicion despues del corte

- `service.py`: 188 lineas
- `business_referrals.py`: 59 lineas

Referencia de mejora:

- `service.py` estaba en 208 lineas antes de separar referrals.
- `service.py` estaba en 345 lineas antes de iniciar los cortes de servicio de creditos.

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

`CreditService` ya no contiene directamente logica de referrals. Esa responsabilidad queda en `CreditBusinessReferrals`.

Estado actual del modulo de creditos:

- `service.py`: fachada de casos de uso.
- `business_purchases.py`: compras Stripe/manual del negocio.
- `business_referrals.py`: referrals del negocio.
- `admin_actions.py`: acciones admin.
- `stripe_webhook.py`: verificacion/parsing Stripe.
- `serializers.py`: salida publica/masked.
- repositorios Postgres e in-memory separados por responsabilidad.

## Riesgo residual

`CreditService` queda suficientemente pequeno para su rol actual. El siguiente paso no deberia ser seguir cortando creditos por inercia. Recomendacion: pasar a otro modulo grande y repetir el mismo criterio de lectura primero.
