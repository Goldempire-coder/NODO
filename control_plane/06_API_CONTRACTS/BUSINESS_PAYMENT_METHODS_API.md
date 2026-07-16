# BUSINESS_PAYMENT_METHODS_API.md

Contrato canonico para lectura y gestion segura de metodos de cobro del negocio en la Mini App Negocio.

Todas las rutas usan prefijo:

```txt
/api/v1
```

## GET /api/v1/business/payment-methods

Devuelve las opciones visuales aprobadas que el negocio puede usar al crear anuncios. La UI no debe pedir ni aceptar un `payment_method_id` escrito manualmente por el usuario.

Auth:

- `Authorization: Bearer <session_jwt>`
- Actor: `business_owner` activo.
- Requiere negocio propio `approved` y asociado al usuario/Telegram autenticado.
- Backend valida ownership; el frontend no decide permisos.

Response 200:

```json
{
  "data": [
    {
      "id": "pm_xxx",
      "label": "Recibo Zelle → Entrego Pago Móvil Bs.",
      "receive_method": "zelle",
      "delivery_method": "pago_movil_ve",
      "receive_display": "Zelle",
      "delivery_display": "Pago Móvil",
      "delivery_currency": "Bs.",
      "status": "approved",
      "is_available": true,
      "limits": {
        "min_amount_usd": "20.00",
        "max_amount_usd": "500.00"
      },
      "masked_account": "***local"
    }
  ],
  "request_id": "req_..."
}
```

Empty response:

```json
{
  "data": [],
  "request_id": "req_..."
}
```

UI empty state:

```txt
Aun no tienes metodos de cobro. Agrega Zelle o USDT TRC20 para publicar anuncios.
```

Rules:

- Devuelve solo metodos de `business_payment_methods.business_id` del negocio propio.
- Devuelve solo metodos `verified_status = approved` y `active = true`.
- No devuelve metodos `pending`, `rejected`, `disabled`, `suspended`, `blocked` o inactivos.
- No devuelve `account_value` completo.
- No devuelve `storage_path`.
- No devuelve datos bancarios completos.
- `masked_account` es opcional y siempre enmascarado.
- `label` debe ser derivado por backend desde metodo recibido y metodo entregado.
- Ejemplos de label:
  - `Recibo Zelle → Entrego Pago Móvil Bs.`
  - `Recibo USDT TRC20 → Entrego Pago Móvil Bs.`
- Si el negocio no existe o no pertenece al actor, responder error seguro sin filtrar existencia ajena.
- Si el negocio no esta aprobado/asociado, responder error seguro.
- `POST /api/v1/business/payment-methods` permite al negocio agregar Zelle o USDT TRC20 propio con PIN desbloqueado e `Idempotency-Key`.
- `PATCH /api/v1/business/payment-methods/{id}` permite editar titular y cuenta/wallet propia con PIN desbloqueado e `Idempotency-Key`.
- `DELETE /api/v1/business/payment-methods/{id}` desactiva el metodo propio con PIN desbloqueado e `Idempotency-Key`.
- La aprobacion de negocio sigue siendo obligatoria y backend valida ownership; el frontend no aprueba metodos por si solo.
- `POST /api/v1/business/ads` mantiene `payment_method_id`, pero el valor debe venir del selector controlado por esta API.

Errores:

- UNAUTHENTICATED
- FORBIDDEN
- BUSINESS_NOT_FOUND
- BUSINESS_NOT_APPROVED
- PAYMENT_METHOD_NOT_APPROVED
- RATE_LIMITED
- NOT_FOUND

Audit:

- Lectura exitosa no requiere audit log por defecto.
- Denegaciones por superficie/RBAC pueden auditar `surface_access_denied` cuando aplique.

Rate limit:

- Aplicar rate limit por actor, negocio, IP y ruta.

Forbidden fields:

- `account_value`
- `storage_path`
- full bank account data
- tokens
- secrets
