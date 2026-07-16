# ACCEPTANCE_CRITERIA.md

El slice queda aceptable para build si:

- Existe modelo `staff_profiles` + `staff_permissions` + `staff_invites`.
- `users.role` no se usa solo para granularidad staff.
- `support_agent`, `support_lead` y `operations_readonly` tienen permisos y prohibiciones claras.
- Staff delegado no puede ejecutar acciones criticas de usuarios, negocios, creditos, disputas, ordenes ni anuncios.
- Endpoints staff estan bajo `/api/v1/admin/staff`.
- Admin Web tiene Staff Center, Staff Detail e Invite Staff.
- Audit/errors/rate limits/security tests estan definidos.
- No hay contrato que permita frontend-only permissions.
