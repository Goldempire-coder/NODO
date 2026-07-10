# BOT_SECURITY.md

## Objetivo

Seguridad del Bot Registro Negocios.

## Reglas

- Bot webhook con secreto/firma obligatoria.
- Bot cliente y Bot Registro Negocios usan tokens separados: `BOT_TOKEN` para cliente y `BUSINESS_INTAKE_BOT_TOKEN` para intake.
- El webhook canonico de intake es `POST /api/v1/business-intake/telegram/webhook/{secret}`.
- El secret de intake debe derivarse/verificarse contra `BUSINESS_INTAKE_BOT_TOKEN`; un secret derivado de `BOT_TOKEN` debe fallar.
- El secret del bot cliente debe fallar si se usa en el webhook de intake, y viceversa.
- Rate limit por Telegram user/chat, telefono y ventana temporal.
- En el flujo MVP, `contact_phone` es el numero de WhatsApp escrito por el solicitante; no se pide contacto compartido de Telegram antes de verificacion owner/admin.
- Telegram ID solo identifica el chat/persona que envia la solicitud; no autoriza acceso al negocio.
- Idempotencia obligatoria por `telegram_chat_id + update_id`; repetir el mismo update no debe crear otra solicitud, otro documento ni otra notificacion.
- No guardar `BOT_TOKEN` ni `BUSINESS_INTAKE_BOT_TOKEN` en frontend, repo, logs, responses ni audit metadata.
- Si `BUSINESS_INTAKE_BOT_TOKEN` no esta configurado, responder `TELEGRAM_BOT_NOT_CONFIGURED`.
- No crear `businesses` activo desde el bot.
- No asociar Telegram ID a negocio aprobado sin accion admin.
- No autorizar acceso a Mini App Negocio; el bot solo captura, notifica y abre la puerta.
- Cualquier boton de apertura requiere validacion posterior por backend con `surface/session`.
- Adjuntos/documentos usan `file_assets.resource_type = business_intake`, `file_assets.file_type = intake_document`, storage privado, MIME `image/jpeg`, `image/png`, `image/webp` o `application/pdf`, maximo 5 MB.
- Documentos Telegram deben descargarse con `getFile` usando `BUSINESS_INTAKE_BOT_TOKEN`; el `file_id` no es URL publica.
- Documentos se deduplican por `telegram_chat_id + update_id + file_unique_id/file_id`.
- Video no esta permitido en MVP; cualquier `video/*` debe responder `BOT_UPLOAD_INVALID`.
- El webhook debe devolver `200 OK` ante errores recuperables de input del usuario y enviar un mensaje correctivo; no debe devolver `400` a Telegram por errores normales del flujo.
- Confirmacion del bot debe decir exactamente: "Solicitud recibida. Revisaremos tu informacion y te avisaremos el siguiente paso."
- El bot no promete aprobacion, acceso ni publicacion de anuncios.

## Audit

- `business_intake_started`
- `business_intake_step_answered`
- `business_intake_submitted`
- `business_intake_document_uploaded`

## Errores

- `BOT_UPLOAD_INVALID`
- `BOT_INPUT_INVALID`
- `TELEGRAM_BOT_NOT_CONFIGURED`
- `TELEGRAM_BOT_SEND_FAILED`
- `BUSINESS_INTAKE_STATUS_INVALID`
- `RATE_LIMITED`
