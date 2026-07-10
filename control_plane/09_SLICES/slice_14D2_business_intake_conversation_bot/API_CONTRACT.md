# API_CONTRACT.md

## Endpoint canonico

```txt
POST /api/v1/business-intake/telegram/webhook/{secret}
```

Auth:
- `{secret}` derivado/verificado contra `BUSINESS_INTAKE_BOT_TOKEN`.
- `BOT_TOKEN` del bot cliente no es valido.
- Si falta `BUSINESS_INTAKE_BOT_TOKEN`, responder `TELEGRAM_BOT_NOT_CONFIGURED`.

Input:
- Update Telegram bruto.
- El backend extrae `update_id`, `message.from.id`, `message.chat.id`, `text`, `photo` y `document`.

Response:
```json
{
  "ok": true,
  "request_id": "req_...",
  "intake_id": "uuid|null",
  "status": "draft|submitted",
  "last_step": "awaiting_referral_code|awaiting_whatsapp_phone|awaiting_documents|submitted",
  "duplicate_update": false
}
```

Errores:
- `FORBIDDEN`
- `RATE_LIMITED`
- `TELEGRAM_BOT_NOT_CONFIGURED`
- `BOT_INPUT_INVALID`
- `BOT_UPLOAD_INVALID`
- `STORAGE_UNAVAILABLE`
- `STORAGE_UPLOAD_FAILED`
- `VALIDATION_ERROR`

Reglas:
- `/start` crea o recupera draft.
- Cada respuesta valida persiste y avanza paso.
- Errores recuperables de input del usuario devuelven webhook `200 OK` y mensaje correctivo al chat.
- El mismo `update_id` no duplica efectos.
- `submitted`, `accepted` y `rejected` no se modifican por mensajes nuevos.
- No crea negocio, access link, roles, anuncios ni creditos.
