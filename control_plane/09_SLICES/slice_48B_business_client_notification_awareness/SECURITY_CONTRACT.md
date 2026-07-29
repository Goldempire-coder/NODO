# Slice 48B Security Contract

Estado: 48B3_IMPLEMENTED_LOCALLY_DURABLE_ATTENTION_READ_STATE

## Objetivo De Seguridad

Avisar rapido sin filtrar informacion sensible ni crear spam operativo.

## Reglas

- Cada usuario solo ve sus propias notificaciones.
- Negocio solo ve eventos de su negocio aprobado y vinculado.
- Cliente solo ve eventos de sus propias ordenes y tickets.
- Las notificaciones no sustituyen autorizacion del endpoint destino.
- Abrir una notificacion debe volver a validar permisos.
- Las rutas deep link no deben exponer secretos.
- Los textos de Telegram deben ser seguros aun si alguien mira la pantalla del
  telefono.
- El cuerpo de mensajes privados no entra a metadata de notificacion.
- Los adjuntos se abren solo por accion explicita y auditada en su flujo propio.
- Los fallos de envio Telegram deben quedar visibles para Admin sin romper la
  accion principal.
- Los jobs 48B1 pueden guardar identificadores de orden/ticket para routing y
  dedupe, pero no `body`, attachment IDs, `file_asset_id`, `storage_path`,
  signed URLs, bancos, wallets, telefonos, documentos, PINs o secretos.
- El deep link solo selecciona el recurso; los endpoints de chat y soporte
  vuelven a validar ownership y acceso activo.
- Los badges 48B2 solo reciben summaries ya autorizados de ordenes y tickets.
- `X-NODO-Surface` debe coincidir con el rol y acceso activo del usuario.
- La respuesta usa `Cache-Control: private, no-store`.
- El aviso interno solo usa tipo, ID, estado y codigo publico de orden.
- Nunca usa cuerpo de chat, cuerpo de soporte, adjuntos o metadata libre.
- 48B3 persiste el reconocimiento de un pendiente por usuario, superficie,
  tipo, recurso y firma opaca.
- El endpoint de reconocimiento revalida ownership y superficie antes de
  escribir estado.
- Una firma vieja no marca como leido un pendiente nuevo.
- El estado persistido no contiene cuerpo de mensaje, asunto, adjuntos,
  comprobantes, bancos, wallets, telefonos, documentos, URLs firmadas, PINs,
  tokens ni razones libres.
- El reconocimiento durable no se presenta como comprobante legal de lectura
  del contenido; solo controla badges operativos.

## Anti Spam Y Dedupe

- Un mismo evento no debe crear duplicados por retry.
- Un mensaje reenviado por idempotencia no debe duplicar badge.
- Si varias actualizaciones ocurren rapido, se pueden agrupar sin perder la
  ruta principal.
- No debe existir polling por cada badge si un endpoint puede devolver todos
  los contadores.

## Auditoria

Builder debe mapear que eventos ya quedan auditados y proponer los faltantes:

- notificacion creada;
- notificacion enviada por Telegram;
- fallo temporal/permanente;
- badge leido;
- item marcado como leido;
- usuario abre ruta desde aviso.

La auditoria no debe guardar cuerpo de mensajes ni metadata libre privada.
