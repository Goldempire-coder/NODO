# SECURITY_CONTRACT.md

## Principio

La notificacion avisa; el detalle admin autorizado muestra la evidencia.

El cuerpo completo del chat no debe copiarse a `admin_notifications`, audit logs, telemetry, breadcrumbs ni logs de error. Solo se entrega bajo una lectura admin explicita y auditada.

## Roles permitidos

El Builder debe inspeccionar la politica actual y proponer el menor alcance compatible con operaciones. Por defecto:

- `super_admin`: puede leer chat de orden desde admin.
- `admin`: puede leer chat de orden desde admin si ya puede ver la orden.
- `support`: solo si el contrato de soporte actual permite ver esa orden o disputa.

Todo otro actor debe recibir rechazo seguro.

## Campos permitidos en respuesta admin

- `message_id`
- `order_id`
- `sender_role`
- `sender_label` seguro
- `body`
- `created_at`
- `delivery_state` o estado equivalente si ya existe
- `attachments` solo con metadata segura:
  - `attachment_id`
  - `filename` seguro o etiqueta generica
  - `mime_type`
  - `size_bytes`
  - `download_available`

## Campos prohibidos

- `storage_path`
- signed URLs en la carga inicial
- tokens
- secretos
- PIN
- wallet privada
- `account_value`
- instrucciones completas de pago fuera del contexto autorizado
- headers internos
- trazas de error

## Adjuntos

Si el chat tiene adjuntos, la pantalla puede mostrar que existen. Abrir o descargar debe ser una accion separada que:

- valide autorizacion nuevamente;
- genere URL temporal o descarga controlada solo en ese momento;
- registre audit log;
- no exponga storage path en UI ni payload persistente.

## Auditoria

Toda carga de mensajes admin debe registrar un evento tipo `admin_order_chat_viewed` o nombre equivalente existente.

Datos minimos:

- actor admin
- `order_id`
- cantidad de mensajes devueltos
- si hubo `highlight_message_id`
- resultado
- `request_id` o `correlation_id`

Datos prohibidos en auditoria:

- cuerpo de mensajes
- valores de adjuntos
- datos bancarios completos
- signed URLs

## Comportamiento ante fallos

- Si falla la carga del chat admin, no debe romper el detalle general de la orden.
- La UI debe mostrar que la conversacion no pudo cargarse y permitir reintentar.
- No debe reemplazar datos reales por mensajes vacios que parezcan ausencia de chat.

