# DATA_CONTRACT.md

## business_intake_requests

Usar tabla existente.

Campos requeridos para 14D2:
- `telegram_user_id`
- `telegram_chat_id`
- `contact_phone`
- `business_phone`
- `status`
- `last_step`
- `last_update_id`
- `business_name`
- `responsible_name`
- `city`
- `operation`
- `banks`
- `methods`
- `min_amount_usd`
- `max_amount_usd`
- `schedule`
- `references`

Reglas:
- `status` activo: `draft`, `submitted`, `accepted`, `rejected`.
- `last_step` usa enum canonico de `STATE_CONTRACT.md`.
- `contact_phone` es el numero de WhatsApp escrito por el solicitante durante `awaiting_whatsapp_phone`.
- `business_phone` es telefono operativo del negocio.
- Cada respuesta valida actualiza el campo correspondiente inmediatamente.

## file_assets

Para documentos del bot:
- `resource_type = business_intake`
- `resource_id = business_intake_requests.id`
- `file_type = intake_document`
- `owner_user_id` asociado al usuario Telegram cuando exista.
- Storage privado obligatorio.
- `storage_path` nunca se expone.

Metadata privada:
- `telegram_update_id`
- `telegram_file_id`
- `telegram_file_unique_id`
- `document_kind`
- MIME original.

MIME permitido:
- `image/jpeg`
- `image/png`
- `image/webp`
- `application/pdf`

Maximo:
- 5 MB.
