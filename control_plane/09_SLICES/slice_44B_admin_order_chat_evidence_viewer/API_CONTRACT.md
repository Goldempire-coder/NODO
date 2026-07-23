# API_CONTRACT.md

## Endpoint dedicado

```txt
GET /api/v1/admin/orders/{order_id}/chat-evidence
```

La conversacion no se agrega al detalle general de orden. Esta ruta existe para
una lectura administrativa explicita, read-only, autorizada y auditada.

## Autorizacion

- Requiere sesion activa y politica `admin read` vigente.
- Cliente y negocio no pueden usar la ruta.
- El deep link y `highlight_message_id` no conceden autorizacion.

## Query

- `cursor`: timestamp opaco devuelto por el endpoint.
- `direction`: `older` o `newer` cuando existe cursor.
- `highlight_message_id`: UUID opcional perteneciente a la misma orden.
- `limit`: 1 a 50; default 50.

Si se solicita un highlight valido sin cursor, el backend incluye ese mensaje en
la pagina inicial. Un mensaje inexistente o perteneciente a otra orden devuelve
`MESSAGE_NOT_FOUND`.

## DTO allowlist

Cada mensaje puede incluir solamente:

- `message_id`
- `sender_role`
- `sender_label`
- `body`
- `status`
- `created_at`
- `highlighted`
- `attachments`

Cada adjunto puede incluir solamente:

- `attachment_id`
- `mime_type`
- `size_bytes`
- `download_available`

La carga inicial no devuelve `file_asset_id`, `storage_path`, signed URLs,
`account_value`, PIN, tokens, secretos ni payloads internos.

## Respuesta y cache

- Mensajes en orden cronologico.
- Maximo 50 mensajes por pagina.
- Cursors separados para mensajes anteriores y posteriores.
- `Cache-Control: private, no-store`.
- Las ordenes en estado terminal conservan evidencia consultable.

## Auditoria

Cada lectura exitosa crea `admin_order_chat_viewed` con:

- actor y rol;
- `order_id`;
- `request_id`;
- cantidad de mensajes;
- direccion de pagina;
- highlight solicitado/encontrado.

El evento no contiene cuerpos de mensajes, metadata privada de adjuntos ni URLs.

## Separacion de fallos

El Admin Web carga este endpoint independientemente del detalle de orden. Un
fallo muestra retry en el panel, pero no invalida ni oculta el detalle general.
