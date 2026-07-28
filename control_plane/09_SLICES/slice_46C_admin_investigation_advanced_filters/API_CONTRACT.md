# Slice 46C API Contract

Estado: DRAFT

## GET /api/v1/admin/investigation/order-candidates

Headers:

- `Authorization: Bearer <admin session>`

Query:

- `client_hint`: string opcional, 3 a 120 caracteres despues de trim.
- `business_hint`: string opcional, 3 a 120 caracteres despues de trim.
- `amount_min_usd`: decimal opcional.
- `amount_max_usd`: decimal opcional.
- `created_from`: timestamp ISO opcional.
- `created_to`: timestamp ISO opcional.
- `order_status`: enum opcional.
- `support_status_group`: `active|archived|all`, default `all`.
- `limit`: entero 1 a 25, default 10.

## Regla De Filtros Minimos

Para evitar busquedas caras o demasiado amplias, la solicitud debe incluir al
menos dos filtros fuertes:

- `client_hint`;
- `business_hint`;
- rango de monto valido;
- ventana de fecha valida;
- `order_status`.

Si solo existe un filtro fuerte, responder:

- `ADMIN_INVESTIGATION_FILTER_REQUIRED`

La ventana de fecha no puede exceder 31 dias salvo `admin` o `super_admin` con
aprobacion posterior en otro slice. En este MVP se rechaza:

- `ADMIN_INVESTIGATION_DATE_RANGE_INVALID`

Los montos deben ser positivos y `amount_min_usd <= amount_max_usd`.

## Respuesta

```json
{
  "data": {
    "items": [
      {
        "type": "order_candidate",
        "order_id": "uuid",
        "public_order_code": "NODO-1234",
        "status": "waiting_payment",
        "amount_usd": "80.00",
        "created_at": "2026-07-28T00:00:00Z",
        "updated_at": "2026-07-28T00:05:00Z",
        "business": {
          "business_id": "uuid",
          "name": "Casa Cambio Centro",
          "status": "approved",
          "action_route": "admin://business/uuid"
        },
        "client": {
          "user_id": "uuid",
          "display_name": "Cliente",
          "telegram_hint": "407*****766",
          "action_route": "admin://user/uuid"
        },
        "signals": [
          "amount_in_range",
          "created_in_window",
          "client_hint_match",
          "support_ticket_related"
        ],
        "payment_report_present": true,
        "support_ticket_count": 1,
        "case_file_route": "admin://case-file/order/uuid",
        "order_route": "admin://order/uuid"
      }
    ],
    "next_cursor": null,
    "truncated": false,
    "disclaimer": "Resultados candidatos. Verifica evidencia antes de decidir."
  },
  "request_id": "req_..."
}
```

## Reglas De Datos

- Telefonos y Telegram se devuelven enmascarados.
- Puede devolver monto, estado, fecha, codigo publico y negocio.
- Puede devolver si existe reporte de pago, pero no su archivo ni datos
  completos.
- No devuelve instrucciones de pago, wallets completas, bancos completos,
  `account_value`, `storage_path`, signed URLs ni `file_asset_id`.
- No devuelve cuerpos de mensajes, asuntos privados largos ni metadata cruda.
- `signals` solo contiene razones deterministicas allowlist.
- No devuelve `score`, `risk_level`, `trust_level`, `severity_hint` ni
  `suggested_next_step`.

## Paginacion Y Costo

- Cursor opaco.
- Filtros se aplican antes de `LIMIT`.
- `limit` maximo 25.
- No offset.
- No full-text sobre mensajes.
- Si el repositorio necesita indice nuevo, Builder debe proponerlo como
  migracion separada con evidencia `EXPLAIN`.

## Roles

- `admin` y `super_admin`: pueden buscar candidatos con campos allowlist.
- `support` activo: solo cuando tenga permisos de soporte/orden enmascarada
  vigentes. Debe recibir campos enmascarados y solo lectura.
- Cliente, negocio y actor sin sesion: rechazo.

## Auditoria

Evento obligatorio:

- `admin_investigation_candidates_searched`

Metadata permitida:

- actor;
- rol;
- presencia de cada filtro, no el valor crudo;
- hash seguro de hints si ya existe patron de hash;
- rango de monto normalizado;
- ventana de fecha;
- conteo devuelto;
- truncado;
- request id.

Metadata prohibida:

- telefono completo;
- texto crudo del hint;
- cuerpos de mensajes;
- datos bancarios completos;
- signed URLs;
- storage paths;
- tokens o secretos.

## Errores

- `ADMIN_INVESTIGATION_FILTER_REQUIRED`: faltan filtros suficientes.
- `ADMIN_INVESTIGATION_DATE_RANGE_INVALID`: ventana invalida o demasiado amplia.
- `ADMIN_INVESTIGATION_AMOUNT_RANGE_INVALID`: montos invalidos.
- `FORBIDDEN`: actor sin permiso.
- `RATE_LIMITED`: exceso de busqueda.

## Cache

- `Cache-Control: private, no-store`
