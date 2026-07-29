# Slice 48B API Contract Draft

Estado: 48B3_IMPLEMENTED_LOCALLY_DURABLE_ATTENTION_READ_STATE

## Principio

Negocio y Cliente necesitan una fuente liviana de pendientes. El contrato final
debe evitar que cada pantalla haga polling pesado por separado.

## Contrato A Mapear

Builder debe confirmar si ya existe algo equivalente antes de proponer endpoints
nuevos.

## Contrato Implementado En 48B2

48B2 usa pendientes operativos derivados de respuestas ya autorizadas mediante:

```http
GET /api/v1/notifications/attention-summary
X-NODO-Surface: business_mini_app | client_mini_app
Cache-Control: private, no-store
```

La respuesta contiene solo:

- `counts.orders`, `counts.support`, `counts.total`;
- items con `kind`, `resource_id`, firma opaca de estado, copy generico y fecha;
- flags `truncated.orders` y `truncated.support`.

- Negocio: ordenes abiertas que requieren atencion y tickets `waiting_user`.
- Cliente: ordenes que requieren accion y tickets `waiting_user`.
- Las ordenes se filtran por ownership/estado y se limitan por
  `updated_at DESC, id DESC`, el mismo criterio operativo de `occurred_at`.
- El reconocimiento al abrir una orden o ticket se guarda en backend mediante
  48B3.
- El reconocimiento ocurre solo despues de cargar correctamente el recurso.
- Si el estado del recurso cambia o llega un mensaje nuevo de la contraparte,
  vuelve a aparecer como pendiente.
- El ultimo valor valido se conserva si una consulta temporal falla.
- Si una seccion supera 50 pendientes, `truncated` obliga a mostrar `50+`;
  el cliente no descarga paginas adicionales.

### Reconocimiento Durable 48B3

```http
POST /api/v1/notifications/attention/acknowledge
X-NODO-Surface: business_mini_app | client_mini_app
Cache-Control: private, no-store
```

Request:

```json
{
  "kind": "order",
  "resource_id": "uuid",
  "signature": "firma opaca recibida en attention-summary"
}
```

Respuesta:

```json
{
  "acknowledged": true
}
```

Reglas:

- El backend revalida que el recurso pertenezca al usuario y superficie.
- La firma debe coincidir con el pendiente vigente; una firma vieja devuelve
  `ATTENTION_SIGNATURE_STALE`.
- El estado guardado solo contiene usuario, superficie, tipo, recurso, firma y
  fechas de reconocimiento.
- La firma opaca se recalcula sin exponer IDs de mensajes en la respuesta.
- No se guardan cuerpos, asuntos, adjuntos, comprobantes, bancos, wallets,
  telefonos, documentos, URLs firmadas, PINs, tokens ni razones libres.
- Si la app se reinstala o se abre en otro dispositivo, el backend conserva el
  reconocimiento mientras la firma sea igual.

Este contrato sigue siendo un mecanismo liviano de pendientes por recurso. No
promete un total historico exacto de mensajes no leidos ni descarga chats para
calcular badges.

### Politica De Refresh

- Un solo scheduler por Mini App.
- Intervalo de 30 segundos.
- Un solo endpoint consulta summaries de Ordenes y Soporte en el mismo ciclo.
- No inicia un ciclo si el anterior sigue en curso.
- Se pausa cuando `document.visibilityState` no es `visible`.
- Al volver a la app ejecuta un refresh inmediato.

## Inventario De Eventos

- `order_created_business`
- `payment_reported_business`
- `order_cancelled_before_payment_business`
- `payment_confirmed_client`
- `payment_rejected_client`
- `order_delivered_client`
- `order_message_created_business`
- `order_message_created_client`
- `support_message_created_participant`
- `support_ticket_resolved_participant`
- `support_ticket_closed_participant`
- `business_status_changed`
- `user_status_changed`

## Contrato Implementado En 48B1

### Chat De Orden

- `order_message_created_business`: Cliente/remitter escribio; recipient es el
  owner del negocio y `target_surface = business_mini_app`.
- `order_message_created_client`: Negocio owner escribio; recipient es el
  cliente/remitter y `target_surface = client_mini_app`.
- Dedupe: `order_id + message_id + notification_type + recipient_user_id`.
- Deep links:
  - `/business/?view=business-chat&order_id={order_id}`;
  - `/?view=order-chat&order_id={order_id}`.

### Soporte

- `support_message_created_participant`: Admin/Soporte respondio con
  `visibility = participants`.
- Respuestas `support_internal` o `admin_internal` no notifican al requester.
- Dedupe: `support_ticket_id + message_id + notification_type + requester`.
- Deep links:
  - `/business/?view=business-support&ticket_id={ticket_id}`;
  - `/?view=support&ticket_id={ticket_id}`.

Los tres tipos usan `notification_jobs`, el sender Telegram existente y su
politica de retry/fallo permanente. Ninguno incluye el cuerpo ni metadata de
adjuntos.

## Restricciones De Privacidad

La respuesta inicial no debe incluir:

- cuerpo del mensaje;
- comprobantes;
- datos bancarios;
- wallets;
- telefonos completos;
- documentos;
- `storage_path`;
- `file_asset_id`;
- signed URLs;
- PINs, tokens o secretos;
- razones administrativas libres.

## Reglas De Costo

- No hacer polling si la pestana esta oculta.
- Evitar refresh solapado.
- Un solo endpoint liviano debe alimentar badges globales.
- Pantallas detalladas pueden refrescar solo cuando estan visibles.
- No descargar adjuntos ni conversaciones completas para calcular badges.
- Intervalo implementado: 30 segundos.
