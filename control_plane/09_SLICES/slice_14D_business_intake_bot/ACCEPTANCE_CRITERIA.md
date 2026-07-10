# ACCEPTANCE_CRITERIA.md

Para aprobar build 14D:

- Contrato y codigo usan solo estados `draft/submitted/accepted/rejected`.
- Video no es aceptado en MVP.
- Contacto Telegram valida `contact.user_id == telegram_user_id`.
- `contact_phone` y `business_phone` estan separados.
- Updates de Telegram son idempotentes por `telegram_chat_id + update_id`.
- Documentos usan storage privado y `file_assets.file_type = intake_document`.
- Bot no aprueba, no da acceso, no crea anuncios, no acredita creditos.
- Pruebas de seguridad y contrato pasan.
