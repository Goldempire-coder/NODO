# DATA_CONTRACT.md

## business_intake_requests

Campos requeridos para 14D:

- id
- telegram_user_id
- telegram_chat_id
- contact_phone
- business_phone
- referral_code
- status
- last_step
- last_update_id
- business_name
- responsible_name
- city
- operation
- banks_json
- methods_json
- min_amount_usd
- max_amount_usd
- schedule_text
- references_json
- submitted_at
- created_at
- updated_at

## Estados

Activos en 14D:

- draft
- submitted
- accepted
- rejected

`under_review` y `archived` son post-MVP/legacy y no deben usarse como estados activos del bot 14D.

## Contacto

- `contact_phone` viene del contacto compartido de Telegram.
- `business_phone` es el telefono operativo declarado por el negocio.
- `contact_phone` y `business_phone` no son equivalentes.
- El contacto compartido debe cumplir `contact.user_id == telegram_user_id`.

## Conversacion e idempotencia

- `last_step` guarda el paso actual.
- `last_update_id` guarda el ultimo update procesado.
- `telegram_user_id + telegram_chat_id` identifican la conversacion.
- `telegram_chat_id + last_update_id` impide duplicar solicitudes, archivos, audit y notificaciones.

## Documentos

- Usar `file_assets`.
- `file_assets.resource_type = business_intake`.
- `file_assets.resource_id = business_intake_requests.id`.
- `file_assets.file_type = intake_document`.
- Storage privado obligatorio.
- MIME permitido: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`.
- Tamano maximo: 5 MB.
- Video queda post-MVP y debe rechazarse con `BOT_UPLOAD_INVALID`.
- `storage_path` nunca se expone en API, frontend, bot messages, logs ni audit.
