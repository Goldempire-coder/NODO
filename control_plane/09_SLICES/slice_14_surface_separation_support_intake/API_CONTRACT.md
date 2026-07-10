# API_CONTRACT.md

## Contratos canonicos

- `SURFACE_SESSION_API.md`
- `BUSINESS_INTAKE_API.md`
- `SUPPORT_API.md`
- `ADMIN_API.md` para composicion admin.
- `USERS_API.md` para perfil y superficie visible.
- `BUSINESS_PAYMENT_METHODS_API.md` para metodos aprobados del negocio en selector seguro.

## Reglas

- Todas las rutas activas usan `/api/v1`.
- Backend calcula RBAC/capabilities por superficie.
- Mutaciones sensibles requieren `Idempotency-Key`, reason cuando aplique, rate limit y audit.
- Bot usa secreto/firma de webhook.
- Admin web no vive dentro de Mini App Cliente.
- Mini App Negocio usa `GET /api/v1/business/payment-methods` para mostrar metodos aprobados propios.
- `POST /api/v1/business/ads` mantiene `payment_method_id`, pero la UI debe obtenerlo del selector backend y no pedirlo manualmente.
- En 14B no hay endpoints de negocio para crear, editar, aprobar, deshabilitar o borrar metodos de pago.
