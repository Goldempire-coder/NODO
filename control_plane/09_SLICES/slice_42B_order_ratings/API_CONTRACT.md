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

La orden debe estar `completed` con uno de estos motivos backend-authoritative:

- `manual_confirmed`;
- `auto_completed_after_24h`;
- `admin_resolved`, solo si existe una disputa asociada ya resuelta y no queda
  disputa `open|in_review`.

Motivos ausentes, legacy o desconocidos devuelven `RATING_NOT_ALLOWED`.

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
      "publication_status": "withheld_pending_snapshot",
      "label": "Reputación protegida"
    }
  },
  "request_id": "req_..."
}
```

El ejemplo devuelve las mismas 5 estrellas enviadas solo al cliente que creo el
rating. `business_reputation` es una proyeccion estable sin tier ni agregados
dinamicos. La respuesta tampoco incluye `risk_level`, `trust_level`, senales
antifraude ni contadores internos.

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
Este bloque solo pertenece al detalle de la orden del cliente propietario; no
se agrega a DTOs de orden del negocio.

`confirm-received` conserva este bloque en su respuesta. La Mini App Cliente lo
muestra como accion compacta dentro del chat completado y vuelve a consultarlo
mediante este detalle cuando se reabre la conversacion.

## Compatibilidad de orden marketplace

`sort=trust` y `sort=speed` siguen aceptados por compatibilidad, pero hasta que
exista snapshot publico durable son aliases de `sort=rate`. Ninguno usa
agregados, tier, confianza o velocidad vivos. La regla completa permanece en
`ADS_API.md`.
