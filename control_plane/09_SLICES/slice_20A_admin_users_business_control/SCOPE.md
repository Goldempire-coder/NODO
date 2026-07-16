# SCOPE.md

## Incluye

- `GET /api/v1/admin/users`.
- `GET /api/v1/admin/users/{id}`.
- `POST /api/v1/admin/users/{id}/suspend`.
- `POST /api/v1/admin/users/{id}/reactivate`.
- `POST /api/v1/admin/users/{id}/block`.
- `GET /api/v1/admin/businesses/{id}/access-links`.
- `GET /api/v1/admin/users/{id}/access-links`.
- Reuso de endpoints admin existentes para crear/suspender/reactivar/revocar/bloquear access links.
- A-10 Admin Web users/remitters como pantalla desktop operativa.
- Tests de RBAC, masking, audit, idempotencia y estado.

## No incluye

- Soporte/tickets real.
- Chat admin real.
- Cost center.
- APM.
- Roles finos nuevos.
- Deploy o produccion.
- Cambios a ordenes, creditos, pagos, disputas, Base USDC, bots o lifecycle de anuncios.
- Nuevas superficies Mini App.
- READY_FOR_REAL_USE.
