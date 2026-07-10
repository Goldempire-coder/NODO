# SECURITY_CONTRACT.md

## Reglas

- Backend es autoridad de acceso.
- Bot no autoriza.
- Frontend obedece `surface/session`.
- Query param `?surface=business` no autoriza.
- `businesses/me` no reemplaza `surface/session`.
- No exponer `telegram_id` publico, `storage_path`, tokens, secretos ni datos bancarios completos.
- Denegaciones usan errores seguros y auditan `surface_access_denied` cuando aplique.
- Mutaciones admin sobre links requieren reason, idempotencia, RBAC y audit.
