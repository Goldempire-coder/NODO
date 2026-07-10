# Architecture Review - Orders Payment Flow Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica del flujo de pago del remitente fuera de `OrderService`.

No se cambiaron reglas de ordenes, endpoints, payloads, frontend, migraciones, contratos, storage, servicios reales ni deploy.

## Archivos modificados

- `apps/api/app/modules/orders/payment_flow.py`
- `apps/api/app/modules/orders/service.py`

## Cambio realizado

- Se creo `OrderPaymentFlow`.
- `OrderService` conserva sus metodos publicos y delega:
  - `payment_instructions`
  - `upload_payment_evidence`
  - `report_payment`
- La revelacion de instrucciones, subida de evidencia privada, creacion de payment report, audit events e idempotencia del reporte quedaron agrupadas en `payment_flow.py`.
- La interfaz de rutas no cambio.

## Medicion despues del corte

- `service.py`: 388 lineas
- `payment_flow.py`: 234 lineas
- `business_ops.py`: 245 lineas

Referencia de mejora:

- `service.py` estaba en 562 lineas antes de separar payment flow.
- `service.py` estaba en 784 lineas antes de iniciar cortes de ordenes.

## Validacion ejecutada

- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_payment_instructions_reports.py apps\api\tests\test_order_creation.py apps\api\tests\test_business_order_ops.py -q`
  - Resultado: `23 passed, 1 warning`
- `python -m ruff check apps\api\app\modules\orders apps\api\tests\test_payment_instructions_reports.py apps\api\tests\test_order_creation.py apps\api\tests\test_business_order_ops.py`
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

`OrderService` ya no mezcla directamente:

- operaciones del negocio
- instrucciones/evidencia/reporte de pago del remitente

Estado actual del modulo de ordenes:

- `service.py`: crear orden, detalle/listado, extension, cancelacion y delegacion.
- `business_ops.py`: superficie negocio.
- `payment_flow.py`: instrucciones, evidencia y reporte de pago.
- `helpers.py`: UUID/profiling compartido.
- builders existentes: planes/respuestas/audit metadata.

## Riesgo residual

`OrderService` conserva la creacion de orden y operaciones de waiting_payment. El siguiente candidato de lectura es separar `create_order` en un caso de uso propio si el corte no duplica profiling/cache/audit. No tocar por inercia; leer primero.
