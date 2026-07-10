# DATA_CONTRACT.md

## Tablas nuevas

- `business_intake_requests`
- `business_access_links`
- `support_tickets`
- `support_messages`
- `support_ticket_events`

## File assets

- Business intake: `file_assets.resource_type = business_intake`, `file_assets.file_type = intake_document`.
- Support ticket: `file_assets.resource_type = support_ticket`.
- Support message: `file_assets.resource_type = support_message`.

No crear storage publico ni exponer `storage_path`.

Business intake MVP:
- `contact_phone` es el telefono compartido por Telegram.
- `business_phone` es el telefono operativo declarado por el negocio.
- `last_step` y `last_update_id` son obligatorios para el flujo conversacional/idempotente.
- MIME permitido: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`.
- Tamano maximo: 5 MB.
- Video queda post-MVP.

## Business access links

- Tabla canonica para autorizar Mini App Negocio.
- Ver `DATA_MODEL_MASTER.md`, `DATABASE_CONSTRAINTS.md`, `ENUMS_AND_STATUS_MASTER.md` e `INDEXES.md`.
- No reemplaza `businesses.owner_user_id`; lo complementa con estado de acceso de usuario/Telegram.
