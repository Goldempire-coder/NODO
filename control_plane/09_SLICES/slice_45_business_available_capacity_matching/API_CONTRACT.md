# API_CONTRACT.md

Este documento define el contrato objetivo. El Builder debe mapear el estado actual antes de implementar y reportar si algun endpoint existente entra en conflicto.

## Business capacity

### GET /api/v1/business/capacity

Devuelve la capacidad operativa del negocio autenticado.

Response:

```json
{
  "data": {
    "business_id": "uuid",
    "availability_status": "online",
    "declared_available_capacity_usd": "40.00",
    "reserved_capacity_usd": "30.00",
    "effective_available_capacity_usd": "10.00",
    "min_order_amount_usd": "20.00",
    "max_order_amount_usd": "100.00",
    "daily_limit_usd": "1000.00",
    "daily_remaining_usd": "970.00",
    "updated_at": "timestamp",
    "capabilities": {
      "can_go_online": true,
      "can_accept_new_orders": false
    }
  },
  "request_id": "req_..."
}
```

### PUT /api/v1/business/capacity

Actualiza disponibilidad y capacidad declarada.

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: required
X-Request-Id: required or generated
```

Request:

```json
{
  "availability_status": "online",
  "declared_available_capacity_usd": "40.00"
}
```

Rules:

- Actor: `business_owner`.
- Solo negocio propio.
- Negocio debe estar aprobado y no suspendido/bloqueado.
- `declared_available_capacity_usd >= 0`.
- No usar float para dinero.
- No permitir declarar por encima de limites operativos sin regla documentada.
- No permitir bajar el declarado por debajo de reservas activas ni de la suma
  de `amount_max_usd` de anuncios `active|in_order`.
- Si queda debajo de `min_order_amount_usd`, el negocio puede quedar online pero no debe aceptar nuevas ordenes.
- Auditar `business_capacity_updated`.

Errores:

- UNAUTHENTICATED
- FORBIDDEN
- BUSINESS_NOT_FOUND
- BUSINESS_NOT_APPROVED
- BUSINESS_SUSPENDED
- BUSINESS_BLOCKED
- CAPACITY_AMOUNT_INVALID
- IDEMPOTENCY_KEY_REQUIRED
- IDEMPOTENCY_CONFLICT
- RATE_LIMITED

## Marketplace search

### GET /api/v1/ads/search

Debe conservar su contrato actual y agregar filtro backend por capacidad.

Query relevante:

```txt
amount_usd=20..100
```

Nueva regla:

```txt
business.effective_available_capacity_usd >= amount_usd
business.availability_status = online
```

El DTO publico puede agregar:

```json
{
  "availability": {
    "status": "online",
    "label": "Online",
    "can_cover_requested_amount": true
  }
}
```

No debe exponer `declared_available_capacity_usd`, `reserved_capacity_usd` ni `effective_available_capacity_usd` al cliente sin aprobacion explicita.

## Order creation

### POST /api/v1/orders

Debe revalidar capacidad en backend aunque el anuncio haya aparecido en busqueda.

Nueva regla:

```txt
amount_usd <= effective_available_capacity_usd
```

Al crear la orden debe crear una reserva ligada a la orden. La reserva debe ser transaccional e idempotente.

Errores nuevos:

- BUSINESS_CAPACITY_INSUFFICIENT
- BUSINESS_OFFLINE
- BUSINESS_CAPACITY_RESERVATION_CONFLICT

## Admin

### GET /api/v1/admin/businesses/{business_id}/capacity

Devuelve vista completa para investigacion operativa.

Debe incluir:

- declarado;
- reservado;
- efectivo;
- limites;
- reservas activas con `order_id`, monto y estado;
- ultima actualizacion;
- actor de ultima actualizacion si aplica.

### PUT /api/v1/admin/businesses/{business_id}/capacity

Permite ajuste manual de capacidad operativa declarada por Admin/Super Admin.
Los limites por operacion y diario conservan su endpoint administrativo
existente y no se mezclan en este `PUT`.

Rules:

- Motivo opcional salvo que una politica futura lo exija.
- Audit log obligatorio.
- No toca creditos ni pagos.
- No declara ni confirma fondos reales.

## Cache y freshness

- Search puede cachear datos no sensibles, pero crear orden nunca usa cache como autoridad.
- Respuestas de capacidad propia y admin deben usar `Cache-Control: private, no-store`.
