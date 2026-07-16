# slice_20C_internal_staff_roles_BUILDER_REPORT

## Estado final

READY_FOR_OWNER_REVIEW

No se declaro READY_FOR_REAL_USE. No se hizo deploy.

## Scope autorizado

Construir staff interno granular para delegar operacion en Admin Web sin entregar permisos peligrosos.

## Que se construyo

- Modelo backend `staff_profiles`, `staff_permissions`, `staff_invites`.
- Migracion reversible `0020_slice_20C_internal_staff_roles`.
- Modulo backend separado `app.modules.staff` con:
  - modelos
  - schemas
  - presenters
  - repositorio in-memory
  - repositorio Postgres
  - service
  - routes
- Endpoints bajo `/api/v1/admin/staff`:
  - `GET /api/v1/admin/staff`
  - `GET /api/v1/admin/staff/{id}`
  - `POST /api/v1/admin/staff/invites`
  - `POST /api/v1/admin/staff/{id}/activate`
  - `POST /api/v1/admin/staff/{id}/suspend`
  - `POST /api/v1/admin/staff/{id}/revoke`
  - `POST /api/v1/admin/staff/{id}/permissions`
  - `GET /api/v1/admin/staff/{id}/activity`
- Enforcement backend:
  - Solo `super_admin` crea/invita/activa/suspende/revoca staff y actualiza permisos.
  - `admin` puede leer staff.
  - `support`/staff delegado no administra staff.
  - Mutaciones staff requieren `Idempotency-Key`, reason, rate limit y audit.
  - Permisos peligrosos quedan bloqueados por backend.
- Integracion con soporte:
  - `support` delegado necesita `staff_profiles.status=active` y permiso activo para operar tickets.
  - `admin` y `super_admin` conservan autoridad existente.
  - Staff revocado pierde permisos inmediatamente.
- Admin Web:
  - Staff Center.
  - Staff Detail.
  - Invite Staff.
  - Matriz simple de permisos/scopes.
  - Activar/suspender/revocar y reemplazar permisos con reason/confirmacion.

## Que NO se construyo

- No SSO corporativo.
- No observability/costos nuevos.
- No reglas nuevas de soporte.
- No cambios a ordenes, anuncios, creditos, pagos, bots o disputas.
- No Mini App Cliente.
- No Mini App Negocio.
- No deploy.
- No READY_FOR_REAL_USE.

## Archivos modificados/creados por 20C

- `database/migrations/0020_slice_20C_internal_staff_roles.up.sql`
- `database/migrations/0020_slice_20C_internal_staff_roles.down.sql`
- `apps/api/app/modules/staff/__init__.py`
- `apps/api/app/modules/staff/models.py`
- `apps/api/app/modules/staff/presenters.py`
- `apps/api/app/modules/staff/schemas.py`
- `apps/api/app/modules/staff/repository.py`
- `apps/api/app/modules/staff/memory_repository.py`
- `apps/api/app/modules/staff/postgres_repository.py`
- `apps/api/app/modules/staff/service.py`
- `apps/api/app/modules/staff/routes.py`
- `apps/api/app/main.py`
- `apps/api/app/modules/support/routes.py`
- `apps/api/app/modules/support/service.py`
- `apps/api/tests/test_internal_staff_roles.py`
- `apps/api/tests/test_support_ticket_center.py`
- `apps/web/src/api/admin.ts`
- `apps/web/src/hooks/admin-web/adminWebTypes.ts`
- `apps/web/src/hooks/admin-web/useAdminStaffModel.ts`
- `apps/web/src/hooks/useAdminWebModel.ts`
- `apps/web/src/screens/admin-web/AdminStaffScreens.tsx`
- `apps/web/src/screens/admin-web/AdminWebScreens.tsx`
- `governance/builder_reports/slice_20C_internal_staff_roles_BUILDER_REPORT.md`
- `evidence/slice_runs/slice_20C_internal_staff_roles_evidence.md`
- `evidence/slice_runs/slice_20C_internal_staff_roles_test_results.json`

## Decisiones de implementacion

- `users.role` sigue siendo rol base. No se agregaron `support_agent`, `support_lead` ni `operations_readonly` a `users.role`.
- Si `POST /admin/staff/invites` recibe `target_user_id` existente, activo y con rol base compatible, crea tambien el `staff_profile` activo y permisos iniciales. Si no hay `target_user_id`, queda como invitacion pendiente sin dar acceso.
- `support` ya no opera tickets solo por `users.role`; requiere perfil staff activo y permisos activos.
- `staff_activity` no se creo como tabla; se lee desde audit logs, como contrato MVP.
- La lista de permisos prohibidos existe solo como control backend (`FORBIDDEN_STAFF_PERMISSIONS`), no como permisos concedibles.

## Validaciones ejecutadas

- `python -m pytest apps/api/tests/test_internal_staff_roles.py apps/api/tests/test_support_ticket_center.py -q --tb=short`: PASS, `9 passed, 1 warning`.
- `python -m pytest apps/api/tests -q`: PASS, `192 passed, 1 warning in 38.08s`.
- `python -m ruff check apps/api scripts`: PASS, `All checks passed!`.
- `python -m compileall apps/api apps/web/src scripts`: PASS.
- `corepack pnpm --filter @nodo/web build`: PASS.
- Scan frontend/staff source/build:
  - sin secretos.
  - sin `storage_path`.
  - sin `account_value`.
  - sin private keys.
  - sin seed phrases.
  - sin bot tokens.
- Scan Admin Web:
  - sin imports Mini App indebidos en Staff screens/model.
  - sin `ClientWorkspace`.
  - sin `BusinessMiniAppWorkspace`.
  - sin Telegram SDK/UI en Admin Web.
- Scan permisos peligrosos:
  - Staff frontend no contiene permisos peligrosos.
  - Backend contiene esos strings solo en `FORBIDDEN_STAFF_PERMISSIONS` como lista de bloqueo.

## Riesgos residuales

- La activacion por invite para `target_user_id` existente queda implementada como activacion directa por `super_admin`; si el owner quiere un flujo de aceptacion de invite por el empleado, eso requiere slice futuro.
- No se implemento SSO ni login corporativo.
- La actividad staff es read model basico sobre audit; no es analitica completa.
- El worktree tenia cambios previos no relacionados; este reporte lista solo archivos tocados para 20C.

## Confirmaciones

- No deploy.
- No READY_FOR_REAL_USE.
- No Mini App Cliente.
- No Mini App Negocio.
- No cambios a reglas de soporte fuera de enforcement staff contratado.
- No cambios a ordenes, anuncios, creditos, pagos, bots ni disputas.
