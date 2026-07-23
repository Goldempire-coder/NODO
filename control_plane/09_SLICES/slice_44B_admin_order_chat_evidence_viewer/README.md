# slice_44B_admin_order_chat_evidence_viewer

status: READY_FOR_VALIDATOR_REVIEW

## Objetivo

Permitir que Admin revise la conversacion completa de una orden desde el dashboard cuando una alerta de evasion del chat abre el detalle de orden.

El slice anterior detecta y avisa sin guardar el cuerpo completo del mensaje en la notificacion. Este slice cierra la parte operativa: el admin debe poder ver la evidencia real en una pantalla autorizada, auditada y segura.

## Riesgo que reduce

- Admin recibe alerta pero no puede revisar el contexto completo.
- La evidencia queda dispersa entre backend, logs y chat de usuario.
- Se termina copiando cuerpo de mensajes sensibles dentro de notificaciones para compensar una UI incompleta.
- Soporte no puede reconstruir que paso antes de una disputa.

## Que construye

- Vista read-only de mensajes de orden dentro del detalle admin de orden, o endpoint admin dedicado si el Builder demuestra que es mas limpio.
- Panel de chat scrollable, compacto y separado del resumen de orden.
- Highlight opcional del mensaje que disparo la alerta cuando se abre desde `admin_notifications`.
- Lectura paginada o limitada para evitar payloads grandes.
- Audit log de lectura admin de conversacion de orden.
- Pruebas de autorizacion, redaccion, no fuga de adjuntos privados y navegacion desde notificacion.

## Que no toca

- No permite que admin envie mensajes dentro del chat de orden.
- No bloquea mensajes.
- No cierra conversaciones.
- No cambia estados de orden.
- No cambia pagos, Base USDC, creditos, Zelle, ratings ni reputacion.
- No cambia el detector anti-evasion salvo que haga falta pasar un identificador seguro de highlight.
- No mete el cuerpo completo del mensaje en `admin_notifications`.
- No hace deploy.
- No ejecuta migraciones sin aprobacion explicita.

## Contrato operativo

Cuando una notificacion de tipo `order_chat_off_platform_solicitation` abre `admin://order/{order_id}`, el dashboard debe cargar el detalle de orden y ofrecer un panel de conversacion read-only.

La notificacion sigue siendo redacted: contiene senal canonica, `order_id`, `message_id`, `rule_id`, severidad y rol. El texto completo solo se obtiene desde un endpoint admin autorizado, con auditoria y sin escribirse en logs.

## Criterios de aceptacion

- Abrir una alerta anti-evasion desde la campana lleva al detalle de orden correcto.
- El detalle admin muestra un panel de chat read-only con mensajes cronologicos.
- Si existe `message_id` de alerta, el mensaje queda destacado sin romper la ruta normal.
- El cuerpo completo del mensaje no aparece en `admin_notifications`, audit logs, telemetry ni logs de error.
- El endpoint rechaza usuarios no admin o sin permiso.
- La respuesta no expone `storage_path`, signed URLs, `account_value`, PIN, tokens, wallet privada ni datos bancarios completos.
- La UI no crece infinitamente: el chat tiene contenedor scrollable.
- Los adjuntos se muestran como metadata segura y solo se abren/descargan por una accion autorizada separada, si aplica.

## Evidencia esperada

- Tests backend de admin chat read autorizado y denegado.
- Tests de que `admin_notifications` mantiene el cuerpo redactado.
- Tests de que el payload admin no expone paths internos ni signed URLs.
- Test frontend o estatico de que `admin://order/{id}` puede abrir detalle y activar panel de chat.
- Build web y suite API pasan.

## Implementacion

- Endpoint dedicado `GET /api/v1/admin/orders/{order_id}/chat-evidence`.
- Consulta read-only limitada a 50 mensajes y con inclusion del highlight.
- DTO de adjuntos por allowlist, sin paths ni URLs iniciales.
- Audit `admin_order_chat_viewed` sin cuerpo de mensajes.
- Hook y panel admin independientes; un fallo no rompe el detalle de orden.
- Navegacion desde `admin://order/{id}` conserva `metadata.message_id`.
