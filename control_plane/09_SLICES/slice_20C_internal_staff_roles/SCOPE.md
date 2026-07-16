# SCOPE.md

## Incluye

- `staff_profiles`, `staff_permissions`, `staff_invites`.
- Staff roles internos: `support_agent`, `support_lead`, `operations_readonly`, `admin`, `super_admin`.
- Permisos granulares de soporte y lectura limitada.
- Admin Web Staff Center, Staff Detail e Invite Staff.
- `STAFF_API.md`.
- Audit events `staff_*`.
- QA de permisos, masking, revocacion y prohibiciones criticas.

## No incluye

- SSO corporativo.
- Exportaciones sensibles.
- Staff en Mini Apps.
- Permitir staff delegado resolver disputas, ajustar creditos, aprobar negocios, bloquear usuarios o mutar `business_access_links`.
- Cambios de reglas de ordenes, creditos, anuncios, pagos, disputas o soporte 20B.
- Deploy.
- READY_FOR_REAL_USE.
