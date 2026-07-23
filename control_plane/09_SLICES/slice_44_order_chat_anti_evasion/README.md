# slice_44_order_chat_anti_evasion

status: READY_FOR_OWNER_REVIEW

## Objetivo

Detectar mensajes del negocio que intenten mover una orden fuera de NODO y avisar al admin sin bloquear el chat ni alterar el estado de la orden.

## Riesgo que reduce

- Negocio intenta cerrar transacciones por fuera de la plataforma.
- NODO pierde evidencia de la conversacion.
- Soporte/admin no detecta patrones de evasion hasta que el cliente reclama.

## Que construye

- Detector backend de frases de salida fuera de NODO en chat de orden.
- Alerta interna en `admin_notifications`.
- Evento auditable sin cuerpo completo del mensaje.
- Ruta admin `admin://order/{id}` para abrir la orden desde la campana.
- Pruebas de no duplicacion por idempotencia y redaccion de contactos.

## Que no toca

- No bloquea mensajes.
- No cierra conversaciones.
- No cambia estados de orden.
- No cambia pagos, Base USDC, creditos, Zelle ni ratings.
- No agrega migracion.
- No cambia reglas de disputa ni auto-completado 24h.
- No hace deploy.

## Contrato operativo

Si el remitente es `business_owner` y el mensaje contiene una invitacion a operar fuera de NODO, el backend conserva el mensaje normal para ambas partes y crea una alerta interna para admin.

El audit log solo conserva identificadores, regla y severidad. El texto completo del mensaje no se escribe en audit logs.

## Evidencia esperada

- `test_business_chat_off_platform_phrase_is_allowed_but_alerts_admin_without_leaking_body`
- `test_remitter_off_platform_phrase_does_not_create_business_solicitation_alert`
- `test_business_chat_whatsapp_phone_alert_redacts_contact_value`
- `test_admin_operational_notifications_frontend_and_migration_contracts`

