# SCOPE.md

## Incluye

- Configuracion contractual de `BUSINESS_INTAKE_BOT_TOKEN`.
- Webhook separado `POST /api/v1/business-intake/telegram/webhook/{secret}`.
- Handler conversacional paso a paso.
- Persistencia parcial en `business_intake_requests`.
- Descarga de `photo` y `document` desde Telegram con `getFile`.
- Storage privado via `file_assets.resource_type = business_intake`, `file_type = intake_document`.
- Idempotencia por `telegram_chat_id + update_id`.
- Dedupe de documentos por `file_unique_id/file_id`.
- Audit events de intake.
- Tests de bot separado, pasos, documentos y prohibiciones.

## No Incluye

- Mini App Cliente.
- Mini App Negocio.
- Admin Web nuevo.
- Crear negocio activo.
- Cambiar `users.role`.
- Crear `business_access_links`.
- Publicar anuncios.
- Acreditar creditos.
- Dar acceso a Mini App Negocio.
- Deploy.
- READY_FOR_REAL_USE.

