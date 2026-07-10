# Architecture Refactor Report - Orders Serializers Split

## Estado

PASSED_AFTER_REFACTOR

## Objetivo

Separar serializacion/payloads publicos de `orders/service.py` sin cambiar reglas de ordenes, estados, creditos, anuncios, pagos, disclaimers ni endpoints.

## Cambios realizados

- Cree `apps/api/app/modules/orders/serializers.py`.
- Movi al nuevo modulo:
  - masking de telefono/documento/titular
  - masking de tx hash
  - capabilities de orden negocio
  - payload publico de orden cliente
  - payload de orden negocio
  - payload de receptor para negocio
  - payload de payment report
  - payload de orden resumida para payment report
- `orders/service.py` ahora llama funciones puras de serializacion en vez de tener builders internos.
- Elimine del service funciones internas ya movidas:
  - `_capabilities`
  - `_business_order_public`
  - `_business_receiver_public`
  - `_business_payment_report_public`
  - `_public_order`
  - `_payment_report_public`
  - `_payment_report_order_public`

## Medicion despues del corte

- `orders/service.py`: 886 lineas
- `orders/serializers.py`: 147 lineas
- Funciones largas que siguen pendientes:
  - `create_order`: 124 lineas
  - `report_payment`: 96 lineas
  - `confirm_business_payment`: 105 lineas

## Validacion ejecutada

- Tests especificos de ordenes: `23 passed, 1 warning`
- Backend pytest completo: `133 passed, 1 warning`
- Ruff: passed
- Compileall: passed
- Frontend build: passed

## Scope no tocado

- No cambie transiciones de orden.
- No cambie creditos.
- No cambie status de anuncios.
- No cambie payment reports.
- No cambie storage.
- No cambie copy/disclaimers.
- No cambie frontend.
- No hice deploy.
- No declare `READY_FOR_REAL_USE`.

## Riesgo residual

El service de ordenes sigue concentrando el core operacional. El siguiente corte recomendado debe ser mas delicado: separar side effects de crear orden o confirmar pago. Recomiendo empezar por `create_order`, extrayendo validacion/preparacion de campos sin tocar la transaccion ni efectos de anuncio.
