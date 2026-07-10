# SCOPE.md

## Incluye

- Webhook/handlers del Bot Registro Negocios.
- Inicio y continuacion de `business_intake_requests`.
- Captura de Telegram ID, chat ID y contacto compartido.
- Validacion de contacto `contact.user_id == telegram_user_id`.
- Formulario guiado con estado conversacional.
- Upload privado de documentos de intake.
- Creacion de solicitud `submitted` para revision admin.
- Notificacion segura al admin.
- Audit logs e idempotencia por Telegram update.

## No incluye

- Aprobar negocios.
- Crear negocios activos automaticamente.
- Crear `business_access_links`.
- Dar acceso a Mini App Negocio.
- Crear anuncios.
- Acreditar creditos.
- Procesar pagos reales.
- Admin Web nuevo.
- Mini App Cliente o Mini App Negocio.
- Video en MVP.
- READY_FOR_REAL_USE.
