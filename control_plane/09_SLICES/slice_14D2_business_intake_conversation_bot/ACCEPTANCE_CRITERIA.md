# ACCEPTANCE_CRITERIA.md

- Webhook separado existe bajo `/api/v1/business-intake/telegram/webhook/{secret}`.
- `BUSINESS_INTAKE_BOT_TOKEN` esta contratado como secreto backend.
- Pasos conversacionales canonicos implementados sin improvisar.
- Persistencia parcial funciona.
- Documentos Telegram se descargan y guardan en storage privado.
- Idempotencia por update y dedupe de documentos funcionan.
- No se crea negocio activo, rol, access link, anuncio, credito ni acceso.
- Tests y scans obligatorios pasan.
- No se declara READY_FOR_REAL_USE.

