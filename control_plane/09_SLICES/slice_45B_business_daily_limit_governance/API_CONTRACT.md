# API_CONTRACT.md

Este documento define el contrato objetivo de 45B. Builder debe mapear primero el estado actual de 45A y reportar si ya existe parte de este contrato antes de implementar.

## Business capacity response

`GET /api/v1/business/capacity` debe permitir que el negocio entienda su situacion diaria sin exponer datos a clientes.

Response objetivo:

```json
{
  "data": {
    "business_id": "uuid",
    "availability_status": "online",
    "declared_available_capacity_usd": "300.00",
    "reserved_capacity_usd": "120.00",
    "effective_available_capacity_usd": "180.00",
    "min_order_amount_usd": "20.00",
    "max_order_amount_usd": "100.00",
    "daily_limit_usd": "1000.00",
    "daily_reserved_usd": "200.00",
    "daily_consumed_usd": "300.00",
    "daily_remaining_usd": "500.00",
    "daily_window": {
      "timezone": "UTC",
      "starts_at": "timestamp",
      "ends_at": "timestamp"
    },
    "capabilities": {
      "can_accept_new_orders": true,
      "daily_limit_reached": false
    }
  },
  "request_id": "req_..."
}
```

Si el sistema aun no separa `daily_reserved_usd` y `daily_consumed_usd`, Builder debe reportarlo como brecha de contrato antes de tocar codigo.

## Admin daily limit view

El contrato existente se amplia de forma compatible:

```txt
GET /api/v1/admin/businesses/{business_id}/capacity
```

Debe devolver:

- limite diario;
- reservado activo, aunque la reserva haya nacido en un dia UTC anterior;
- consumido hoy;
- restante hoy;
- ventana diaria;
- hasta 50 ordenes que explican el calculo;
- `daily_orders_truncated` para indicar que hay mas registros;
- actor de ultimo ajuste si aplica.

La lista es limitada. No usar listas ilimitadas ni incluir datos de pago.

## Marketplace search

`GET /api/v1/ads/search` debe filtrar en backend antes de `LIMIT`:

```txt
amount_usd <= daily_remaining_usd
```

DTO publico permitido:

```json
{
  "availability": {
    "status": "online",
    "can_cover_requested_amount": true
  }
}
```

DTO publico prohibido:

```json
{
  "daily_remaining_usd": "500.00",
  "daily_reserved_usd": "200.00",
  "daily_consumed_usd": "300.00"
}
```

## Order creation

`POST /api/v1/orders` debe revalidar dentro de la misma operacion que crea la orden:

```txt
amount_usd <= daily_remaining_usd
```

Errores esperados:

- `BUSINESS_DAILY_LIMIT_EXCEEDED`
- `BUSINESS_CAPACITY_INSUFFICIENT`
- `BUSINESS_OFFLINE`
- `BUSINESS_CAPACITY_RESERVATION_CONFLICT`

`BUSINESS_DAILY_LIMIT_EXCEEDED` se usa solo cuando la capacidad inmediata
alcanza, pero el presupuesto diario no. El frontend puede mostrar el mismo
mensaje seguro usado para capacidad insuficiente.

Si el calculo no puede completarse, crear orden falla cerrado. No existe
fallback cliente ni calculo alternativo en frontend.

## Headers y cache

- Las respuestas propias del negocio deben usar `Cache-Control: private, no-store`.
- Las respuestas Admin deben usar `Cache-Control: private, no-store`.
- El marketplace puede cachear datos publicos, pero crear orden nunca usa cache como autoridad.
