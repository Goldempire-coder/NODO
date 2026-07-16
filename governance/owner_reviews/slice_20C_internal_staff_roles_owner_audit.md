# slice_20C_internal_staff_roles - Owner Audit

## Estado

PASSED_AFTER_OWNER_AUDIT_FIX

## Resultado

El slice 20C construye staff interno granular con backend como autoridad. La separación `staff_profiles`, `staff_permissions` y `staff_invites` está alineada con los contratos y no agrega roles nuevos a `users.role`.

## Fixes aplicados durante owner audit

### 1. Compatibilidad de permisos por rol interno

Problema encontrado:

- El backend validaba que el permiso existiera y que no estuviera en la deny-list peligrosa.
- Pero no validaba que el permiso fuera compatible con `staff_profiles.staff_role`.
- Ejemplo de riesgo: un `operations_readonly` podía recibir `reply_support_ticket` si un `super_admin` se equivocaba al configurar permisos.

Fix:

- Agregué `ROLE_ALLOWED_PERMISSIONS` en `apps/api/app/modules/staff/service.py`.
- `operations_readonly` queda limitado a permisos de lectura enmascarada/limitada.
- `support_agent` queda limitado a operación básica de soporte.
- `support_lead` puede operar cola de soporte solo con permisos activos.
- `admin` y `super_admin` conservan permisos compatibles con sus roles base.

### 2. Compatibilidad entre rol base y staff_role

Problema encontrado:

- Un usuario base `support` podía ser activado como `staff_role=admin` si el payload lo pedía.

Fix:

- Agregué `ROLE_BASE_COMPATIBILITY`.
- `support_agent`, `support_lead` y `operations_readonly` requieren rol base `support`.
- `admin` requiere rol base `admin`.
- `super_admin` requiere rol base `super_admin`.

### 3. Asignación de tickets a soporte sin staff activo

Problema encontrado:

- `assign_ticket` permitía asignar un ticket a un usuario `support` activo aunque no tuviera perfil staff activo.
- Ese usuario no podía operar luego por falta de permisos, pero dejaba una asignación operativamente inválida.

Fix:

- `apps/api/app/modules/support/service.py` ahora rechaza asignar a un `support` sin `staff_profiles.status=active`.
- Error: `SUPPORT_ASSIGNEE_INVALID`.

## Tests agregados

- `test_staff_role_permission_and_base_role_compatibility_are_enforced`
- `test_support_ticket_assignment_requires_active_staff_profile_for_support_assignee`

## Validaciones ejecutadas

- `python -m pytest apps/api/tests/test_internal_staff_roles.py apps/api/tests/test_support_ticket_center.py -q --tb=short`: PASS, `11 passed, 1 warning`.
- `python -m pytest apps/api/tests -q`: PASS, `194 passed, 1 warning`.
- `python -m ruff check apps/api scripts`: PASS.
- `python -m compileall apps/api apps/web/src scripts`: PASS.
- `corepack pnpm --filter @nodo/web build`: PASS.
- Scan frontend source/build: sin secretos, `storage_path`, `account_value`, private keys, seed phrases, bot tokens ni claims prohibidos.

## Riesgos residuales

- No hay flujo de aceptación de invitación por empleado; `super_admin` activa usuarios existentes compatibles.
- No hay SSO corporativo.
- `staff_activity` sigue siendo read model básico sobre audit logs.

## Confirmaciones

- No hice deploy.
- No declaré `READY_FOR_REAL_USE`.
- No construí Mini App Cliente ni Mini App Negocio.
- No cambié reglas de órdenes, anuncios, créditos, pagos, bots ni disputas.
