# Architecture Review - Credits Business Purchases Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica de compras/pagos de creditos del negocio fuera de `CreditService`.

No se cambiaron reglas de negocio, endpoints, payloads, frontend, migraciones, contratos, storage, servicios reales ni deploy.

## Archivos modificados

- `apps/api/app/modules/credits/business_purchases.py`
- `apps/api/app/modules/credits/service.py`

## Cambio realizado

- Se creo `CreditBusinessPurchases`.
- `CreditService` conserva sus metodos publicos y delega:
  - `create_stripe_checkout`
  - `create_manual_payment`
- La validacion de paquete, metodo de pago manual, proof file, storage privado, auditoria e idempotencia de compras quedaron agrupadas en `business_purchases.py`.
- La generacion de checkout URL tambien salio del servicio principal.
- La interfaz de rutas no cambio.

## Medicion despues del corte

- `service.py`: 208 lineas
- `business_purchases.py`: 131 lineas

Referencia de mejora:

- `service.py` estaba en 265 lineas antes de separar compras/pagos de negocio.
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

`CreditService` ya no contiene directamente la logica de compra Stripe ni pago manual con comprobante. Esa responsabilidad queda en `CreditBusinessPurchases`.

El servicio principal queda mas cercano a una fachada de casos de uso:

- wallet/ledger
- purchases
- referrals
- Stripe webhook orchestration
- admin actions

## Riesgo residual

El siguiente candidato claro es referrals dentro de `CreditService`:

- `referrals`
- `apply_referral`

Ese corte deberia ser pequeno y puede dejar `CreditService` cerca de 170 lineas.
