# BUSINESS_INTAKE_API.md

## Objetivo

API para Bot Registro Negocios y Panel Admin Web.

## Bot endpoints

### POST /api/v1/business-intake/telegram/webhook/{secret}

Endpoint canonico para el Bot Registro Negocios separado.

Auth/secret:
- `{secret}` debe derivarse/verificarse contra `BUSINESS_INTAKE_BOT_TOKEN`.
- `BOT_TOKEN` pertenece al bot cliente y no es valido en este endpoint.
- Si `BUSINESS_INTAKE_BOT_TOKEN` no esta configurado, responder `TELEGRAM_BOT_NOT_CONFIGURED`.

Payload:
- Update Telegram bruto firmado por el secret del webhook.
- El handler debe extraer `update_id`, `message.from.id`, `message.chat.id`, `text`, `photo` y `document` segun corresponda.

Reglas:
- Solo procesa flujo de intake de negocios.
- `/start` crea o recupera draft y deja `last_step = awaiting_referral_code`.
- Cada respuesta valida se guarda inmediatamente en `business_intake_requests`.
- `last_step` avanza por la secuencia canonica del contrato de 14D2.
- El bot acepta `photo` y `document` con MIME permitido; descarga archivos con Telegram `getFile` usando `BUSINESS_INTAKE_BOT_TOKEN`.
- Rechaza `video`, `audio`, `voice`, `animation` y MIME no permitido con `BOT_UPLOAD_INVALID`.
- El webhook responde `200 OK` ante errores recuperables del usuario (`BOT_INPUT_INVALID`, `BOT_UPLOAD_INVALID`, `RATE_LIMITED`) y envia mensaje correctivo al chat para evitar retries infinitos de Telegram.
- No crea negocio activo.
- No cambia `users.role`.
- No crea `business_access_links`.
- No publica anuncios.
- No acredita creditos.
- No entrega acceso a Mini App Negocio.

Response:
```json
{
  "ok": true,
  "request_id": "req_...",
  "intake_id": "uuid|null",
  "last_step": "awaiting_referral_code|awaiting_whatsapp_phone|awaiting_documents|submitted",
  "status": "draft|submitted",
  "duplicate_update": false
}
```

Errores:
- `TELEGRAM_BOT_NOT_CONFIGURED`
- `FORBIDDEN`
- `RATE_LIMITED`
- `BOT_INPUT_INVALID`
- `BOT_UPLOAD_INVALID`
- `STORAGE_UNAVAILABLE`
- `STORAGE_UPLOAD_FAILED`
- `VALIDATION_ERROR`

Audit:
- `business_intake_started`
- `business_intake_step_answered`
- `business_intake_document_uploaded`
- `business_intake_submitted`

### Pasos conversacionales 14D2

Orden canonico de `last_step`:
1. `start`
2. `awaiting_referral_code`
3. `awaiting_whatsapp_phone`
4. `awaiting_documents`
5. `submitted`

Validaciones:
- `referral_code` se guarda como texto corto y no ejecutable.
- `contact_phone` es el numero de WhatsApp escrito por el solicitante; no se valida como contacto compartido de Telegram en este flujo MVP.
- Mensajes demasiado largos o fuera del paso actual responden como error recuperable: webhook `200 OK` mas mensaje correctivo en Telegram.

Idempotencia:
- `telegram_chat_id + update_id` repetido no duplica cambios.
- Documento repetido no duplica `file_assets`; deduplicar por `telegram_chat_id + update_id + file_unique_id/file_id`.
- Una respuesta repetida con nuevo `update_id` puede corregir el paso actual si todavia no avanzo; no puede modificar una solicitud `submitted`, `accepted` o `rejected`.

### POST /api/v1/business-intake/start

Headers:
- `X-NODO-Bot-Webhook-Secret` o firma equivalente.

Payload:
```json
{
  "telegram_user_id": "string",
  "telegram_chat_id": "string",
  "telegram_update_id": 123456,
  "referral_code": "string|null"
}
```

Response 201:
```json
{ "data": { "id": "uuid", "status": "draft", "last_step": "awaiting_referral_code" } }
```

Rules:
- Idempotente por `telegram_chat_id + telegram_update_id`.
- Repetir el mismo update devuelve la misma solicitud/resultado seguro y no duplica audit ni notificacion.
- No requiere contacto todavia; solo inicia draft.

Audit: `business_intake_started`.

### POST /api/v1/business-intake/{id}/contact

Legacy/internal. No es el flujo activo del Bot Registro Negocios MVP.

Rules:
- El flujo activo usa `awaiting_whatsapp_phone` desde el webhook conversacional.
- No se debe pedir "compartir contacto de Telegram" al negocio antes de verificacion owner/admin.

### POST /api/v1/business-intake/{id}/submit

Payload:
```json
{
  "telegram_update_id": 123458,
  "telegram_user_id": "123456789",
  "telegram_chat_id": "123456789",
  "business_name": "string",
  "responsible_name": "string",
  "city": "string",
  "business_phone": "string",
  "operation": "buy_usd|sell_usd|both",
  "banks": ["string"],
  "methods": ["zelle", "usdt_trc20"],
  "min_amount_usd": "decimal",
  "max_amount_usd": "decimal",
  "schedule": "string",
  "references": ["string"]
}
```

Response 200:
```json
{ "data": { "id": "uuid", "status": "submitted", "message": "Solicitud recibida. Revisaremos tu informacion y te avisaremos el siguiente paso." } }
```

Rules:
- `contact_phone` requerido previamente y persistido desde el paso `awaiting_whatsapp_phone`.
- `telegram_update_id`, `telegram_user_id` y `telegram_chat_id` deben validarse contra la solicitud.
- Idempotente por `telegram_chat_id + telegram_update_id`.
- No crea negocio activo.
- No publica anuncios.
- No promete aprobacion.
- Admin queda notificado.

Audit: `business_intake_submitted`.

### POST /api/v1/business-intake/{id}/documents

Multipart fields:
- `file`
- `document_kind`: `identity_document | rif_document | local_image | social_reference | other_reference`
- `telegram_update_id`

Rules:
- Storage privado.
- `file_assets.resource_type = business_intake`.
- `file_assets.resource_id = business_intake_requests.id`.
- `file_assets.file_type = intake_document`.
- MIME permitido: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`.
- Tamano maximo: 5 MB.
- Video queda post-MVP; `video/*` y otros MIME deben responder `BOT_UPLOAD_INVALID`.
- Idempotente por `telegram_chat_id + telegram_update_id`; repetir upload no duplica archivo ni audit.
- `storage_path` nunca se expone.

Audit: `business_intake_document_uploaded`.

## Admin endpoints

### GET /api/v1/admin/business-intake

Query:
- `status`
- `cursor`
- `limit` 1..50

Response:
- Cursor pagination con datos enmascarados.

### GET /api/v1/admin/business-intake/{id}

Rules:
- Admin/super_admin/support pueden ver detalle segun RBAC.
- Documentos completos solo con signed URL corta y audit.

Audit: `business_intake_viewed_by_admin`.

### POST /api/v1/admin/business-intake/{id}/accept

Headers:
- `Authorization`
- `Idempotency-Key`

Payload:
```json
{
  "reason": "string",
  "create_business": true,
  "approve_business": true,
  "public_business_name": "Casa Cambio Centro"
}
```

Rules:
- Solo admin/super_admin.
- Reason obligatorio.
- Si `create_business = true`, `public_business_name` es obligatorio y se guarda en `businesses.business_name`; ese es el nombre visible en la app cliente/marketplace.
- Si la solicitud ya tiene `created_business_id`, admin puede enviar `approve_business = true` con `create_business = false` para aprobar y vincular ese negocio existente.
- Bot intake no crea negocio activo ni autoriza acceso.
- Admin puede crear negocio desde intake y decidir explicitamente si queda `pending` o `approved`.
- `approve_business = true` solo es valido si admin reviso la evidencia requerida y queda auditado; si queda `pending`, no hay acceso a Mini App Negocio.
- Asociar Telegram/persona/negocio usa el Telegram ID canonico guardado en la solicitud; el backend crea o recupera ese usuario, asigna `business_owner` y deja `business_access_links.status = active`.
- Activar acceso solo es valido cuando `business.verification_status = approved` y el link queda `active`.
- Si el negocio queda `pending`, el link puede crearse como `suspended`/no operativo o diferirse hasta aprobacion; no debe permitir `business_mini_app`.
- El bot puede notificar "Tu negocio fue aprobado" solo despues de aprobacion admin y link activo confirmado por backend.
- La respuesta incluye `created_business`, `access_link_created`, `approval_notification_sent` y el negocio publico resultante.

Audit:
- `business_intake_accepted`
- `business_created_from_intake` si se crea negocio
- `business_access_linked` si se crea link activo
- `business_telegram_linked` queda legacy alias/no canonico para nuevas implementaciones; usar `business_access_linked`

### POST /api/v1/admin/business-intake/{id}/reject

Headers:
- `Authorization`
- `Idempotency-Key`

Payload:
```json
{ "reason": "string" }
```

Rules:
- Solo admin/super_admin.
- Reason obligatorio.
- No crea negocio.

Audit: `business_intake_rejected`.

### POST /api/v1/admin/business-intake/{id}/delete

Headers:
- `Authorization`
- `Idempotency-Key`

Payload:
```json
{ "reason": "string" }
```

Rules:
- Solo admin/super_admin.
- Reason obligatorio.
- Usar solo cuando una solicitud de negocio fue enviada mal y debe salir del panel.
- El registro de intake se elimina de la cola operativa.
- Los documentos asociados se marcan como borrados/no visibles.
- `audit_logs` son append-only y se preservan.
- No borra usuarios, negocios, access links, ordenes, creditos ni auditoria.

Audit: `business_intake_deleted`.
