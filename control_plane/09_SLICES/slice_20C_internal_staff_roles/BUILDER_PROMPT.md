# BUILDER_PROMPT.md

MODO: BUILD_SLICE

Slice: `slice_20C_internal_staff_roles`

Construir solo delegacion interna segura para Admin Web:

- `staff_profiles`
- `staff_permissions`
- `staff_invites`
- endpoints `/api/v1/admin/staff`
- Staff Center, Staff Detail e Invite Staff
- audit/events/tests

No construir:

- cambios a ordenes, creditos, anuncios, pagos, disputas o soporte 20B.
- permisos criticos para staff delegado.
- staff en Mini App Cliente o Mini App Negocio.
- deploy.
- READY_FOR_REAL_USE.

Regla central:

`users.role` es rol base; permisos finos viven en `staff_profiles` y `staff_permissions`.
