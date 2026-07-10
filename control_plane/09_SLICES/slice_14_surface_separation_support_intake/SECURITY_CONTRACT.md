# SECURITY_CONTRACT.md

## Contratos

- `SURFACE_ACCESS_POLICY.md`
- `BOT_SECURITY.md`
- `SUPPORT_SECURITY.md`
- `RBAC_PERMISSION_MATRIX.md`
- `SENSITIVE_DATA_POLICY.md`
- `RATE_LIMIT_POLICY.md`
- `AUDIT_LOG_POLICY.md`

## Reglas

- RBAC backend obligatorio.
- Admin web separado de Mini App Cliente.
- Negocio solo entra si aprobado/asociado.
- Desde 14B1, "aprobado/asociado" significa `business.verification_status = approved` y `business_access_links.status = active` para el usuario/Telegram validado.
- `GET /api/v1/surface/session` es el gate canonico; `/api/v1/businesses/me` no autoriza superficie.
- Bot no crea negocio activo.
- Bot no autoriza acceso.
- Support no ejecuta acciones criticas fuera de RBAC.
- Storage privado para documentos/adjuntos.
- No exponer `storage_path`, tokens, secretos ni datos sensibles completos.
- Metodos de pago de negocio se leen solo por backend ownership y negocio aprobado/asociado.
- Responses de metodos de pago no exponen `account_value`, `storage_path` ni datos bancarios completos.
- La UI de negocio no acepta IDs manuales de metodos para publicar anuncios.
- La Mini App Negocio no crea, edita, aprueba, deshabilita ni borra metodos de pago en 14B.
