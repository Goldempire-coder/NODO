# UI_CONTRACT.md

## Mini App Negocio

- Debe llamar `GET /api/v1/surface/session` antes de hidratar workspace.
- Debe renderizar estados: no linked business, pending/not approved, suspended, blocked, user/access suspended, link revoked, link blocked, allowed.
- Debe deshabilitar acciones segun capabilities backend.
- No debe mostrar onboarding publico, verificacion propia ni create business.
- No debe inferir permisos por `role` local.
