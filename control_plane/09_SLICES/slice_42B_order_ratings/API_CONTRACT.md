# API_CONTRACT.md

## POST /api/v1/orders/{order_id}/rating

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
```

Request:

```json
{
  "stars": 5
}
```

`stars` es entero estricto 1..5. No se aceptan comentarios ni campos extra.

Response 201:

```json
{
  "data": {
    "rating": {
      "id": "uuid",
      "order_id": "uuid",
      "business_id": "uuid",
      "stars": 5,
      "created_at": "timestamp"
    },
    "business_reputation": {
      "tier": "new",
      "label": "Nuevo",
      "rating_avg": "5.00",
      "ratings_count": 1,
      "completed_orders_count": 1,
      "success_rate": "100.00",
      "average_delivery_seconds": null
    }
  },
  "request_id": "req_..."
}
```

El ejemplo devuelve las mismas 5 estrellas enviadas. La respuesta publica no
incluye `risk_level`, `trust_level`, senales antifraude ni contadores internos.

Errores:

- `ORDER_NOT_FOUND` 404 para orden inexistente o ajena;
- `RATING_NOT_ALLOWED` 409 para orden no completada o con disputa abierta;
- `RATING_ALREADY_EXISTS` 409 para rating previo con otra llave;
- `IDEMPOTENCY_KEY_REQUIRED` 400;
- `IDEMPOTENCY_PAYLOAD_MISMATCH` 409;
- `VALIDATION_ERROR` 422;
- `FORBIDDEN` 403 para actor no cliente activo.

## GET /api/v1/orders/{order_id}

Agrega de forma compatible:

```json
{
  "rating": {
    "can_rate": true,
    "already_rated": false,
    "stars": null
  }
}
```

`can_rate` y `already_rated` son calculados por backend. Si ya existe rating,
`can_rate=false`, `already_rated=true` y `stars` contiene el entero guardado.
