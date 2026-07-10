# BOT_ARCHITECTURE.md

## Objetivo

Definir arquitectura del Bot Registro Negocios.

## Separacion de bots

Bots activos:
- Bot cliente: usa `BOT_TOKEN`, atiende la Mini App Cliente y no procesa intake de negocios.
- Bot Registro Negocios: usa `BUSINESS_INTAKE_BOT_TOKEN`, atiende solo captacion de negocios y no abre ni autoriza la Mini App Cliente.

Endpoint canonico 14D2:

```txt
POST /api/v1/business-intake/telegram/webhook/{secret}
```

Reglas:
- `{secret}` se deriva/verifica contra `BUSINESS_INTAKE_BOT_TOKEN` mediante el mismo criterio seguro usado para webhooks Telegram, sin exponer el token.
- Un secret derivado de `BOT_TOKEN` no es valido para el webhook de intake.
- Un secret derivado de `BUSINESS_INTAKE_BOT_TOKEN` no es valido para el webhook del bot cliente.
- El handler de intake debe descargar archivos desde Telegram usando `BUSINESS_INTAKE_BOT_TOKEN`, nunca `BOT_TOKEN`.
- El bot de negocios no procesa comandos cliente ni entrega URL de Mini App Cliente.

## Estructura esperada

```txt
apps/bot/
  app/
    main.py
    handlers/
    services/
    schemas/
    storage/
    notifications/
```

## Responsabilidades

- Validar webhook secret/token.
- Guiar formulario de intake.
- Persistir cada respuesta valida de la conversacion en `business_intake_requests` antes de avanzar de paso.
- Guardar solicitud como `business_intake_requests`.
- Guardar documentos via storage privado/file_assets.
- Persistir estado conversacional por `telegram_user_id`, `telegram_chat_id`, `last_step` y `last_update_id`.
- Procesar updates de Telegram de forma idempotente por `telegram_chat_id + update_id`.
- Descargar `photo`/`document` de Telegram con `getFile`, validar MIME/tamano y guardar en storage privado.
- Notificar admin.
- No crear negocios activos.
- No publicar anuncios.
- No autorizar acceso a Mini App Negocio.
- Botones como "Abrir NODO Negocios" solo abren la superficie; `GET /api/v1/surface/session` decide acceso.

## Seguridad

- `BOT_TOKEN` y `BUSINESS_INTAKE_BOT_TOKEN` son secretos backend/bot runtime y no se exponen a frontend, logs, respuestas, audit metadata ni reportes.
- Webhook secret obligatorio en staging/production.
- Rate limit por Telegram user/contacto.
- Validar contacto compartido de Telegram: `contact.user_id` debe coincidir con `telegram_user_id`.
- No logs con documentos, telefonos completos, tokens o `storage_path`.
