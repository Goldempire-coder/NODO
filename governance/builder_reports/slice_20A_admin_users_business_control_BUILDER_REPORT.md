# BUILDER_REPORT - slice_20A_admin_users_business_control

## Estado final

READY_FOR_OWNER_REVIEW

## Alcance construido

Construido solo `slice_20A_admin_users_business_control`.

Se agrego control operativo de usuarios y accesos de negocio desde Admin Web:

- Busqueda admin de usuarios por telefono, Telegram ID, username, rol y estado.
- Detalle admin de usuario con conteos, negocios relacionados y access links.
- Mutaciones admin de usuario:
  - suspender: `active -> restricted`
  - reactivar: `restricted|dormant -> active`
  - bloquear: `active|restricted|dormant -> blocked`
- Protecciones:
  - `support` read-only/masked.
  - `admin` no muta `admin/super_admin`.
  - `super_admin` protege el ultimo `super_admin active`.
  - `blocked -> active` no se permite en 20A.
- Lectura admin de `business_access_links` por usuario y por negocio.
- Admin Web muestra links de acceso en detalle de negocio y permite crear/suspender/reactivar/revocar/bloquear links existentes.

## Archivos principales

- `apps/api/app/modules/admin/routes.py`
- `apps/api/app/modules/admin/service.py`
- `apps/api/app/modules/admin/postgres_users.py`
- `apps/api/app/modules/admin/user_presenters.py`
- `apps/api/app/modules/admin/memory_repository.py`
- `apps/api/app/core/errors.py`
- `apps/api/tests/test_admin_users_business_control.py`
- `apps/web/src/api/admin.ts`
- `apps/web/src/hooks/admin-web/useAdminUsersModel.ts`
- `apps/web/src/hooks/admin-web/useAdminBusinessesModel.ts`
- `apps/web/src/hooks/useAdminWebModel.ts`
- `apps/web/src/screens/admin-web/AdminUserScreens.tsx`
- `apps/web/src/screens/admin-web/AdminBusinessScreens.tsx`
- `apps/web/src/types/admin.ts`
- `database/migrations/0018_slice_20A_admin_users_business_control.up.sql`
- `database/migrations/0018_slice_20A_admin_users_business_control.down.sql`

## No construido

- Soporte/tickets completos.
- Roles internos de empleados/delegacion.
- Centro de costos/observabilidad.
- UI de chats desde dashboard.
- Deploy.
- Cambios de negocio, cliente, bots, pagos o creditos fuera de 20A.
- `READY_FOR_REAL_USE`.

## Validacion

- Focus test 20A: `3 passed, 1 warning`.
- Pytest acumulado: `183 passed, 1 warning`.
- Ruff: `All checks passed!`.
- Compileall: OK.
- TypeScript: `tsc --noEmit` OK.
- Frontend build: OK.
- Frontend source/build scan: sin secretos, `storage_path`, `account_value` ni claims prohibidos.
- Admin Web scan: sin imports de ClientWorkspace, BusinessMiniAppWorkspace, Telegram MainButton, themeParams ni bottom nav.

## Riesgos residuales

- 20B debe construir soporte/tickets para clientes y negocios.
- 20C debe construir roles internos/delegacion para empleados.
- Observabilidad/costos/errores internos requieren slice posterior dedicado.
- Migracion 0018 no fue aplicada a staging real en este paso.
