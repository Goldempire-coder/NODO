# BUSINESSES_API.md

Contrato canonico de negocio y verificacion.

Todas las rutas usan prefijo:

```txt
/api/v1
```

Todas las rutas requieren `Authorization: Bearer <session_jwt>`.

## Reglas generales

- El backend valida ownership, RBAC, estado actual, rate limit e idempotencia cuando aplique.
- `business.verification_status` solo puede ser: `pending`, `approved`, `rejected`, `suspended`, `blocked`.
- `draft` puede existir solo como estado UI/workflow antes de crear/enviar verificacion.
- El estado de revision pendiente se expresa solo como `pending`.
- `under_review` pertenece a `business.risk_level`, no a `verification_status`.
- No exponer datos sensibles completos salvo permiso especifico.
- No exponer `storage_path`.
- Responses usan `ERROR_CONTRACT.md`.

## Objeto publico de negocio propio

```json
{
  "id": "uuid",
  "owner_user_id": "uuid",
  "business_name": "string",
  "rif": "J-***123",
  "address": "string|null",
  "phone": "+58*******123",
  "country": "VE",
  "verification_status": "pending|approved|rejected|suspended|blocked",
  "trust_level": "new|basic|plus|pro|premium",
  "risk_level": "normal|watch|under_review|restricted|high_risk",
  "max_order_amount_usd": "100.00",
  "daily_limit_usd": "300.00",
  "active_order_limit": 1,
  "approved_at": "timestamp|null",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

Admin puede recibir campos completos solo cuando tenga permiso y el response indique que son datos sensibles.

## POST /api/v1/businesses

Legacy/internal para compatibilidad. No es flujo activo de Mini App Negocio ni endpoint publico de self-onboarding.

La Mini App Negocio no puede crear negocio, auto-registrarse ni iniciar verificacion propia. El flujo activo para negocios nuevos es:

1. Bot Registro Negocios crea `business_intake_requests`.
2. Admin Web revisa.
3. Admin crea/aprueba negocio segun contrato de intake/admin.
4. Admin vincula usuario/Telegram/negocio mediante `business_access_links`.
5. `GET /api/v1/surface/session` habilita o deniega `business_mini_app`.

Este endpoint no debe aceptar creacion publica en runtime real. La implementacion activa debe responder `403 BUSINESS_SELF_ONBOARDING_DISABLED` salvo caminos internos/test fixture explicitamente marcados y fuera de producto.

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-Request-Id: requerido o generado por backend
```

Request:

```json
{
  "business_name": "Casa Cambio Centro",
  "rif": "J-12345678-9",
  "address": "string",
  "phone": "+584121234567",
  "country": "VE"
}
```

Response runtime real:

```json
{
  "error": {
    "code": "BUSINESS_SELF_ONBOARDING_DISABLED",
    "message": "Operacion no disponible desde esta superficie.",
    "details": {}
  },
  "request_id": "req_..."
}
```

Response legacy/internal controlado:

```json
{
  "data": {
    "business": {}
  },
  "request_id": "req_..."
}
```

Rules legacy/internal:

- No debe ser llamado desde Mini App Negocio.
- No debe estar disponible como self-onboarding publico.
- No puede convertir automaticamente usuarios en `business_owner` para acceso real de negocio.
- El acceso real requiere `business_access_links.status = active`.
- Guest no puede crear negocio.
- Un usuario no puede crear multiples negocios activos sin contrato futuro.
- Default:
  - `verification_status = pending`
  - `trust_level = new`
  - `risk_level = normal`
  - `max_order_amount_usd = 100.00`
  - `daily_limit_usd = 300.00`
  - `active_order_limit = 1`
- Auditar `business_created`.
- No crear anuncios, creditos ni ordenes.

## PUT /api/v1/businesses/{id}

Legacy/internal para compatibilidad. No es endpoint activo de edicion publica de negocio.

La edicion operativa de datos visibles del negocio debe quedar en Admin Web o en un contrato futuro especifico de Business Settings. La implementacion activa no debe aceptar mutaciones publicas por owner en runtime real y debe responder `403 BUSINESS_SELF_ONBOARDING_DISABLED`, salvo caminos internos/test fixture fuera de producto.

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-Request-Id: requerido o generado por backend
```

Request:

```json
{
  "business_name": "Casa Cambio Centro",
  "rif": "J-12345678-9",
  "address": "string",
  "phone": "+584121234567",
  "country": "VE"
}
```

Response runtime real:

```json
{
  "error": {
    "code": "BUSINESS_SELF_ONBOARDING_DISABLED",
    "message": "Operacion no disponible desde esta superficie.",
    "details": {}
  },
  "request_id": "req_..."
}
```

Response legacy/internal controlado:

```json
{
  "data": {
    "business": {}
  },
  "request_id": "req_..."
}
```

Rules:

- No debe estar disponible como mutacion publica por owner.
- Estados permitidos: `pending`, `rejected`, `approved`, `suspended`.
- `blocked` no permite update por owner.
- Cambios sobre `approved` deben auditar `business_updated`.
- No permite cambiar `owner_user_id`, `verification_status`, `trust_level`, `risk_level`, limites ni `approved_at` desde owner.

## POST /api/v1/businesses/{id}/verification-documents

Legacy/fuera de Mini App Negocio para nuevos negocios.

El flujo activo de documentos de negocios referidos usa Bot Registro Negocios + `BUSINESS_INTAKE_API.md` con `file_assets.resource_type = business_intake`. La implementacion activa no debe aceptar uploads publicos por owner en runtime real y debe responder `403 BUSINESS_SELF_ONBOARDING_DISABLED`, salvo caminos internos/test fixture fuera de producto.

Headers:

```txt
Authorization: Bearer <session_jwt>
X-Request-Id: requerido o generado por backend
```

Request: `multipart/form-data`

```txt
file: binary
file_type: rif_document|business_license|owner_identity|address_proof
```

Response runtime real: `403 BUSINESS_SELF_ONBOARDING_DISABLED`.

Response legacy/internal controlado:

```json
{
  "data": {
    "file": {
      "id": "uuid",
      "file_type": "rif_document",
      "mime_type": "application/pdf",
      "size_bytes": 12345,
      "created_at": "timestamp"
    }
  },
  "request_id": "req_..."
}
```

Rules:

- No debe estar disponible como upload publico por owner.
- Estados permitidos: `pending`, `rejected`.
- No debe ser usado por Mini App Negocio como onboarding publico.
- Storage privado obligatorio.
- `storage_path` nunca se expone en response.
- MIME permitido: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`.
- Max size: 5 MB.
- Auditar `verification_document_uploaded`.

## POST /api/v1/businesses/{id}/submit-verification

Legacy/fuera de Mini App Negocio para nuevos negocios.

El flujo activo de alta/verificacion de negocios referidos queda en Bot Registro Negocios + Admin Web. La implementacion activa no debe aceptar submit publico por owner en runtime real y debe responder `403 BUSINESS_SELF_ONBOARDING_DISABLED`, salvo caminos internos/test fixture fuera de producto.

Headers:

```txt
Authorization: Bearer <session_jwt>
Idempotency-Key: requerido
X-Request-Id: requerido o generado por backend
```

Request:

```json
{
  "submitted_data": {
    "business_name": "Casa Cambio Centro",
    "rif": "J-12345678-9",
    "address": "string",
    "phone": "+584121234567",
    "country": "VE",
    "document_file_ids": ["uuid"]
  }
}
```

Response runtime real: `403 BUSINESS_SELF_ONBOARDING_DISABLED`.

Response legacy/internal controlado:

```json
{
  "data": {
    "business": {},
    "submission": {
      "id": "uuid",
      "business_id": "uuid",
      "status": "pending",
      "submitted_at": "timestamp"
    }
  },
  "request_id": "req_..."
}
```

Rules:

- No debe estar disponible como submit publico por owner.
- Estados permitidos para submit: `pending`, `rejected`.
- No debe ser usado como pantalla activa de Mini App Negocio.
- No puede existir otra submission `pending` para el mismo negocio.
- Crea `business_verification_submissions.status = pending`.
- `submitted_data_json` guarda snapshot de datos enviados y `document_file_ids`; no guarda `storage_path`.
- Auditar `business_submitted`.

## GET /api/v1/businesses/me

Devuelve negocio propio si existe.

No es gate canonico de acceso para Mini App Negocio. La Mini App Negocio debe llamar primero a `GET /api/v1/surface/session` con `X-NODO-Surface: business_mini_app`.

Response 200:

```json
{
  "data": {
    "business": {}
  },
  "request_id": "req_..."
}
```

Rules:

- Actor autenticado.
- Solo devuelve negocio propio.
- Datos sensibles enmascarados por defecto.

## Metodos de pago del negocio

La lectura operativa de metodos aprobados para la Mini App Negocio esta definida por `BUSINESS_PAYMENT_METHODS_API.md`.

Reglas:

- Negocio solo lee metodos propios aprobados/activos mediante `GET /api/v1/business/payment-methods`.
- La gestion/aprobacion de metodos es admin-controlled en 14B.
- No exponer `account_value`, `storage_path` ni datos bancarios completos.

## Errores esperados

- BUSINESS_NOT_FOUND
- BUSINESS_ALREADY_EXISTS
- BUSINESS_ALREADY_SUBMITTED
- BUSINESS_STATUS_INVALID
- BUSINESS_VERIFICATION_REQUIRED
- BUSINESS_DOCUMENT_REQUIRED
- BUSINESS_DOCUMENT_INVALID
- FORBIDDEN
- UNAUTHENTICATED
- RATE_LIMITED
- IDEMPOTENCY_PAYLOAD_MISMATCH
