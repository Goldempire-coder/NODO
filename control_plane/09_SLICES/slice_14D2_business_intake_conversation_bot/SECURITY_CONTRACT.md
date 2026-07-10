# SECURITY_CONTRACT.md

## Secrets

- `BUSINESS_INTAKE_BOT_TOKEN` es secreto backend.
- Prohibido en frontend, logs, respuestas, audit metadata, screenshots y repositorios.
- `BOT_TOKEN` no puede usarse para el webhook de intake.

## Storage

- Documentos en storage privado.
- Nunca exponer `storage_path`.
- Signed URLs solo para admin/support autorizados segun contrato admin.

## Input

- `telegram_user_id` identifica el chat/persona que envia la solicitud, pero no autoriza acceso de negocio.
- Pedir numero de WhatsApp como texto durante `awaiting_whatsapp_phone`.
- No pedir "compartir contacto de Telegram" en el MVP del Bot Registro Negocios.
- Rechazar video/audio/media no permitida.
- Rechazar archivos mayores a 5 MB.
- Sanitizar textos largos/listas.
- Rate limit por IP, Telegram user y chat.

## Prohibiciones

- No crear `businesses` activos.
- No cambiar roles.
- No crear `business_access_links`.
- No publicar anuncios.
- No acreditar creditos.
- No autorizar Mini App Negocio.
