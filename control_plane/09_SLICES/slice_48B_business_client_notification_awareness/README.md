# Slice 48B - Business And Client Notification Awareness

Estado: 48B3_IMPLEMENTED_LOCALLY_DURABLE_ATTENTION_READ_STATE

## Objetivo

Asegurar que Negocio y Cliente se enteren a tiempo de eventos importantes
dentro y fuera de la Mini App: orden nueva, pago reportado, mensajes del chat,
respuestas de soporte, cierres, cancelaciones y eventos que requieren accion.

El usuario no debe depender de refrescar manualmente, estar mirando una pantalla
exacta o adivinar que algo cambio.

## Problema Que Cubre

NODO ya tiene notificaciones Telegram para algunos eventos de orden y tiene
refrescos dentro de ciertas pantallas, pero la experiencia todavia no se siente
como una app viva:

- El negocio puede no notar una orden nueva si no esta atento.
- Un mensaje nuevo de cliente o negocio puede quedar escondido si la otra parte
  no esta dentro del chat.
- Soporte puede responder y el usuario no ver un aviso claro.
- La barra inferior no tiene burbujas persistentes de pendientes.
- Los avisos actuales son temporales y no equivalen a un inbox de no leidos.

## Resultado Esperado

- Mapa completo de eventos que deben avisar a Negocio y Cliente.
- Decision por evento: Telegram fuera de app, badge dentro de app o ambos.
- Contadores livianos por superficie: ordenes, chat de orden y soporte.
- Banner/toast interno con accion directa para abrir el lugar correcto.
- Badges visibles en navegacion inferior cuando haya pendientes.
- Marcado de leido al abrir la orden, chat o ticket correspondiente.
- Politica economica: polling liviano, pausa si la app esta oculta y sin
  infraestructura nueva salvo aprobacion posterior.
- Notificaciones sin cuerpos privados, bancos, wallets, comprobantes, PINs,
  tokens ni identificadores internos de storage.

## Dependencias

- Ordenes y chat de orden existentes.
- Soporte Cliente/Negocio existente.
- Notification jobs Telegram existentes.
- Mini App Negocio y Mini App Cliente.
- Admin operational notifications solo como referencia, no como inbox de usuario.
- Slice 48A para cancelacion antes de pago.

## No Construir Todavia

Este slice empieza con mapeo. Builder debe inspeccionar y reportar antes de
implementar.

No construir todavia:

- WebSocket, SSE o proveedor push nuevo.
- Cambios financieros, creditos, USDC, Zelle o precios.
- Cambios al estado de orden.
- Borrado de mensajes, tickets, ordenes o evidencia.
- Texto de mensajes privados dentro de notificaciones.
- Descarga automatica de adjuntos.
- Polling agresivo que aumente costo de Redis/API.

## 48B1 Implementado Localmente

- Mensaje Cliente -> Negocio crea aviso Telegram seguro.
- Mensaje Negocio -> Cliente crea aviso Telegram seguro.
- Respuesta Admin/Soporte visible para participantes crea aviso Telegram seguro.
- Replay idempotente no duplica el job.
- Los botones abren el chat o ticket exacto y la API revalida ownership.
- Retry, fallo permanente y alerta Admin reutilizan el sender existente.
- La migracion reversible `0037_business_client_message_notifications` amplía
  solo la allowlist de tipos; no fue ejecutada.

## 48B2 Implementado Localmente

- Badges de pendientes operativos en las barras inferiores de Negocio y Cliente.
- Respuestas de Soporte en `waiting_user` aparecen como pendientes.
- Ordenes en estados accionables aparecen como pendientes segun la superficie.
- Un aviso interno seguro permite abrir la orden o ticket exacto.
- Abrir el recurso reconoce solo ese pendiente durante la sesion.
- Un unico request de awareness tiene objetivo de 15 segundos, solo con la app
  visible, sin refresh solapado y con backoff/jitter ante fallos.
- Si una consulta falla, se conserva el ultimo contador valido y se muestra
  `Sin actualizar`.
- El ciclo de Negocio reemplaza el polling previo de ordenes cada 10 segundos.

48B2 no implementaba persistencia de lectura. 48B3 agrega estado durable de
pendientes por recurso y firma opaca, sin convertirlo en descarga de chats ni
inbox historico completo.

## 48B3 Implementado Localmente

- Abrir correctamente una orden o ticket puede reconocer el pendiente en backend.
- El reconocimiento se guarda por usuario, superficie, tipo de recurso, recurso
  y firma opaca.
- Si la app se cierra y vuelve a abrir, el pendiente reconocido no reaparece
  mientras la firma siga siendo la misma.
- Si llega un mensaje nuevo de la contraparte o cambia el estado operativo, la
  firma cambia y el pendiente vuelve a aparecer.
- No se guarda cuerpo de mensajes, asunto, adjuntos, comprobantes, bancos,
  wallets, telefonos, documentos ni URLs firmadas.
- La migracion reversible `0038_surface_attention_read_state` crea la tabla de
  lectura; no debe ejecutarse sin validacion y aprobacion de deploy.

48B3 sigue siendo un contador liviano de pendientes por recurso. No descarga
conversaciones ni calcula un total historico exacto si una cuenta acumula mas de
50 pendientes por seccion.
