# SECURITY_CONTRACT.md

## Autoridad

El backend es autoridad de auth, RBAC, permisos, ownership, estados, audit e idempotencia.

## Acceso

- `admin`: acceso y mutaciones segun RBAC.
- `super_admin`: acceso y mutaciones criticas segun RBAC.
- `support`: acceso read-only salvo soporte explicito contratado.
- `remitter` y `business_owner`: no pueden entrar a Admin Web.

## Mutaciones sensibles

Requieren:

- backend RBAC
- reason obligatorio
- confirmacion UI
- `Idempotency-Key`
- rate limit
- audit log

Aplica a:

- approve/reject business
- view signed document URL
- resolve dispute
- approve/reject manual credit payment
- admin credit adjustment
- role mutation si existe contrato futuro

## Datos prohibidos

No exponer en UI, logs, respuestas ni bundle:

- `storage_path`
- `account_value` completo
- tokens
- secretos
- signed URLs persistidas
- evidencia privada completa fuera de endpoint autorizado
- datos bancarios completos

## Surface

Admin Web debe ser superficie `admin_web`, separada de Mini App Cliente y Mini App Negocio.
