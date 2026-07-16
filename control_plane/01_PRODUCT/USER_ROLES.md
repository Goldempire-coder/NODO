# USER_ROLES.md

## Superficies por rol

- `remitter`: puede entrar a Mini App Cliente.
- `business_owner`: puede entrar a Mini App Negocio solo si tiene negocio aprobado y `business_access_links.status = active` asociado a su usuario/Telegram validado.
- `admin`: puede entrar a Panel Admin Web Desktop y ejecutar acciones admin contratadas.
- `super_admin`: puede entrar a Panel Admin Web Desktop y ejecutar acciones criticas contratadas.
- `support`: puede entrar a Panel Admin Web Desktop en modo soporte/read-only o acciones de soporte contratadas.
- `guest`: actor derivado/no persistente; no entra a superficies autenticadas.
- `business applicant`: actor descriptivo/no persistente usado solo en Bot Registro Negocios e intake; no es `user.role`.

El rol no basta por si solo para operaciones de negocio: el backend debe validar ownership, negocio aprobado, usuario activo, link activo y superficie `business_mini_app`.

El rol no basta por si solo para admin: el backend debe validar superficie `admin_web`, RBAC y reason/idempotencia cuando aplique.

Roles oficiales MVP:

- remitter
- business_owner
- admin
- super_admin
- support

Roles derivados/no persistentes:

- guest

Roles post-MVP:

- business_operator
- support_readonly

Roles internos staff (no son `users.role`; viven en `staff_profiles.staff_role`):

- support_agent
- support_lead
- operations_readonly
- admin
- super_admin

## Reglas

- `remitter` crea ordenes y reporta pagos.
- `business_owner` publica anuncios y confirma pagos recibidos.
- `admin` aprueba, revisa, suspende y audita.
- `super_admin` maneja permisos criticos y roles admin.
- `support` ve casos y escala, sin acciones criticas.
- `guest` no se guarda en DB; representa una request sin sesion valida.
- La delegacion interna 20C no agrega nuevos valores persistidos a `users.role`; usa `staff_profiles` y `staff_permissions`.
- Staff activo requiere `users.status = active` y `staff_profiles.status = active`.
- Revocar staff no bloquea necesariamente el usuario; bloquear usuario sigue el contrato de admin users.

## Prohibido

- No usar `business` como rol persistente.
- No usar whitelist informal como unico control admin.
- No usar solo `users.role = support` para delegar permisos finos de empleados.
