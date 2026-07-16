# SCOPE.md

## Incluye

- `support_tickets`, `support_messages`, `support_ticket_events`.
- Adjuntos via `file_assets`, sin tabla `support_attachments` en MVP.
- Cliente: crear/listar/ver/responder tickets propios.
- Negocio: crear/listar/ver/responder tickets propios de negocio/orden/anuncio/credito.
- Admin Web: cola, detalle, respuesta, asignacion, escalamiento, resolucion, cierre y signed URL corta para adjuntos.
- RBAC real para remitter, business_owner, support, admin y super_admin.
- Audit events y tests de seguridad.

## No incluye

- Crear o resolver disputas formales.
- Cambiar `orders.status`.
- Mover `credit_wallets` o `credits_ledger`.
- Cambiar `ads.status`.
- Aprobar/rechazar pagos.
- Cambiar roles/usuarios/business access links.
- Chat operativo por orden existente.
- Soporte por canales externos.
- Export sensible.
- Deploy.
- READY_FOR_REAL_USE.
