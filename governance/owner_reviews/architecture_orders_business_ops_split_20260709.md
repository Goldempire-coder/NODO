# Architecture Review - Orders Business Ops Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica de operaciones de negocio fuera de `OrderService`.

No se cambiaron reglas de ordenes, endpoints, payloads, frontend, migraciones, contratos, storage, servicios reales ni deploy.

## Archivos modificados

- `apps/api/app/modules/orders/business_ops.py`
- `apps/api/app/modules/orders/helpers.py`
- `apps/api/app/modules/orders/service.py`

## Cambio realizado

- Se creo `OrderBusinessOps`.
- Se creo `orders/helpers.py` para helpers compartidos:
  - `require_uuid`
  - `profile_enabled`
  - `profile_mark`
  - `profile_attach`
- `OrderService` conserva sus metodos publicos y delega:
  - `business_orders`
  - `business_order_detail`
  - `confirm_business_payment`
  - `reject_business_payment_report`
  - `mark_business_delivered`
- La logica de confirmacion/rechazo/entrega del negocio, timelines, evidencia para negocio, consumo de hold y audit events de negocio quedo agrupada en `business_ops.py`.
- La interfaz de rutas no cambio.

## Medicion despues del corte

- `service.py`: 562 lineas
- `business_ops.py`: 245 lineas
- `helpers.py`: 37 lineas

Referencia de mejora:

- `service.py` estaba en 784 lineas antes de separar operaciones de negocio.

## Validacion ejecutada

- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_business_order_ops.py apps\api\tests\test_order_creation.py apps\api\tests\test_payment_instructions_reports.py -q`
  - Resultado: `23 passed, 1 warning`
- `python -m ruff check apps\api\app\modules\orders apps\api\tests\test_business_order_ops.py apps\api\tests\test_order_creation.py apps\api\tests\test_payment_instructions_reports.py`
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

`OrderService` ya no mezcla directamente la superficie de negocio con la superficie del remitente.

Queda separado:

- `OrderService`: create/detail/mine/extend/cancel/payment instructions/evidence/report payment y delegacion.
- `OrderBusinessOps`: list/detail de ordenes del negocio y operaciones confirm/reject/deliver.
- `orders/helpers.py`: helpers compartidos de UUID y profiling.

## Riesgo residual

`OrderService` sigue grande porque conserva varios flujos de remitente y pago:

- create order
- detail/mine
- extend/cancel
- payment instructions
- payment evidence upload
- payment report
- expiration materialization

Siguiente lectura recomendada: separar payment instructions/evidence/report payment en una unidad `payment_reports.py` o equivalente, porque es un flujo propio distinto de create/cancel/order list.
