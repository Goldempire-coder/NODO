# QA.md

## Pruebas requeridas para build futuro

- Mini App Cliente no muestra ni llama negocio/admin.
- Mini App Negocio rechaza usuario sin negocio aprobado/asociado.
- Admin Web no vive dentro de Mini App Cliente.
- Bot intake no crea negocio activo.
- Bot intake no publica anuncios.
- Bot intake requiere contacto.
- Bot intake valida `contact.user_id == telegram_user_id`.
- Bot intake separa `contact_phone` de `business_phone`.
- Bot intake procesa `telegram_update_id` de forma idempotente.
- Bot intake no duplica solicitud/documento/audit/notificacion al repetir update.
- Bot intake acepta solo imagen/PDF y rechaza video con `BOT_UPLOAD_INVALID`.
- Bot intake guarda documentos con `file_assets.resource_type = business_intake` y `file_type = intake_document`.
- Admin accept intake requiere reason.
- Admin reject intake requiere reason.
- Soporte general no cambia estado de orden.
- Soporte por orden no es disputa.
- Escalamiento a disputa usa contrato de disputa.
- `storage_path` no aparece en API/frontend/logs.
- CORS/origenes separados por superficie.
- RBAC backend niega acciones cross-surface.
- No claims prohibidos de escrow/fondos garantizados.
- business owner ve solo metodos propios aprobados.
- negocio no aprobado no ve metodos.
- metodos pending/rejected/disabled/suspended/blocked no aparecen.
- otro negocio no puede ver metodos ajenos.
- response de metodos no incluye `account_value`.
- response de metodos no incluye `storage_path`.
- B-08 no tiene input manual de `payment_method_id`.
- B-16 no permite crear/editar/aprobar/borrar metodos en 14B.
