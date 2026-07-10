# SECURITY_CONTRACT.md

## Webhook

- Requiere secret token/firma del bot.
- Rate limit obligatorio.
- No confiar en texto libre para permisos.

## Contacto Telegram

- `telegram_user_id` identifica a la persona.
- El contacto compartido debe incluir `contact.user_id`.
- `contact.user_id` debe coincidir exactamente con `telegram_user_id`.
- Si no coincide, responder `BOT_CONTACT_REQUIRED`.

## Storage

- Storage privado obligatorio.
- Signed URLs cortas solo para admin/support autorizado segun contrato.
- No exponer `storage_path`.
- No aceptar video en MVP.

## Autoridad

- El bot no autoriza acceso.
- Admin Web decide aceptacion/rechazo.
- Backend aplica RBAC, audit e idempotencia.
