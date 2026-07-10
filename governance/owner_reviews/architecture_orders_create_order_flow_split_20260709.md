# Architecture Review - Orders Create Order Flow Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica del flujo de creacion de orden fuera de `OrderService`.

No se cambiaron reglas de ordenes, endpoints, payloads, frontend, migraciones, contratos, storage, servicios reales ni deploy.

## Archivos modificados

- `apps/api/app/modules/orders/create_order_flow.py`
- `apps/api/app/modules/orders/service.py`

## Cambio realizado

- Se creo `OrderCreateFlow`.
- `OrderService` conserva el metodo publico `create_order` y delega al nuevo flujo.
- La logica de crear orden, validar anuncio/negocio/metodo de pago/monto, idempotencia de creacion, mover anuncio a `in_order`, limpiar cache marketplace, state event inicial y audit batch quedo agrupada en `create_order_flow.py`.
- La interfaz de rutas no cambio.

## Medicion despues del corte

- `service.py`: 308 lineas
- `create_order_flow.py`: 138 lineas
- `payment_flow.py`: 234 lineas
- `business_ops.py`: 245 lineas

Referencia de mejora:

- `service.py` estaba en 388 lineas antes de separar create order.
- `service.py` estaba en 784 lineas antes de iniciar cortes de ordenes.

## Validacion ejecutada

- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_order_creation.py apps\api\tests\test_ads_marketplace.py apps\api\tests\test_payment_instructions_reports.py -q`
  - Resultado: `31 passed, 1 warning`
- `python -m ruff check apps\api\app\modules\orders apps\api\tests\test_order_creation.py apps\api\tests\test_ads_marketplace.py apps\api\tests\test_payment_instructions_reports.py`
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

El modulo de ordenes ya no tiene un `OrderService` monolitico.

Estado actual:

- `service.py`: fachada central de ordenes, detalle/listado, extension/cancelacion y delegacion.
- `create_order_flow.py`: creacion de orden.
- `payment_flow.py`: instrucciones/evidencia/reporte de pago.
- `business_ops.py`: operaciones de negocio.
- `helpers.py`: UUID/profiling compartido.

## Riesgo residual

`OrderService` conserva extension/cancelacion/materializacion de expiracion. Por ahora no recomiendo seguir cortando ordenes: el servicio ya esta en 308 lineas y las responsabilidades grandes estan separadas.

Siguiente modulo recomendado para lectura: `business_intake`, porque mezcla bot conversacional, endpoints REST, admin review, documentos y storage.
