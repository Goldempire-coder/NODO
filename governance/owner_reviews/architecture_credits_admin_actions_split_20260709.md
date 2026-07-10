# Architecture Review - Credits Admin Actions Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica de acciones admin de creditos fuera de `CreditService`.

No se cambiaron reglas de negocio, endpoints, payloads, frontend, migraciones, contratos, storage, servicios reales ni deploy.

## Archivos modificados

- `apps/api/app/modules/credits/admin_actions.py`
- `apps/api/app/modules/credits/service.py`

## Cambio realizado

- Se creo `CreditAdminActions`.
- `CreditService` conserva sus metodos publicos admin y delega:
  - `admin_list_purchases`
  - `admin_approve_purchase`
  - `admin_reject_purchase`
  - `admin_adjust`
- La validacion RBAC admin, idempotencia, lookup de purchase, auditoria admin y ajuste manual quedaron agrupados en `admin_actions.py`.
- La interfaz de rutas no cambio.

## Medicion despues del corte

- `service.py`: 265 lineas
- `admin_actions.py`: 104 lineas

Referencia de mejora:

- `service.py` estaba en 320 lineas antes de separar acciones admin.
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

`CreditService` ya no contiene directamente las operaciones admin de revision/aprobacion/rechazo/ajuste. Queda como fachada de casos de uso de creditos, mientras las acciones administrativas viven en una unidad separada.

## Riesgo residual

`CreditService` todavia contiene varios casos de uso de negocio:

- wallet/ledger
- Stripe checkout
- manual payment
- referrals
- apply referral
- Stripe webhook orchestration

Siguiente lectura recomendada: separar pagos/compras de negocio (`create_stripe_checkout` y `create_manual_payment`) si el corte reduce complejidad sin duplicar validaciones.
