# API_CONTRACT.md

Contrato canonico: `control_plane/06_API_CONTRACTS/BUSINESS_INTAKE_API.md`.

## Bot endpoints

- `POST /api/v1/business-intake/start`
- `POST /api/v1/business-intake/{id}/contact`
- `POST /api/v1/business-intake/{id}/submit`
- `POST /api/v1/business-intake/{id}/documents`

Todos requieren secreto/firma de webhook del bot. Ninguno requiere ni concede sesion de Mini App Negocio.

## Reglas

- `start` crea o devuelve draft idempotente.
- `contact` valida `contact_user_id == telegram_user_id` y guarda `contact_phone`.
- `submit` requiere contacto previo y guarda `business_phone` separado.
- `documents` usa storage privado con `file_assets.resource_type = business_intake` y `file_type = intake_document`.
- Todos procesan `telegram_update_id` idempotentemente.
- Ningun endpoint crea negocio activo, publica anuncios, acredita creditos o crea acceso operativo.

## Errores

- BUSINESS_INTAKE_NOT_FOUND
- BUSINESS_INTAKE_STATUS_INVALID
- BOT_CONTACT_REQUIRED
- BOT_UPLOAD_INVALID
- STORAGE_UNAVAILABLE
- STORAGE_UPLOAD_FAILED
- RATE_LIMITED
- FORBIDDEN
- VALIDATION_ERROR
