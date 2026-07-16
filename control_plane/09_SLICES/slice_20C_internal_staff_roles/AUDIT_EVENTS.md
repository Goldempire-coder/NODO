# AUDIT_EVENTS.md

Eventos obligatorios:

- `staff_invite_created`
- `staff_invite_expired`
- `staff_activated`
- `staff_suspended`
- `staff_revoked`
- `staff_permissions_updated`
- `staff_activity_viewed`
- `staff_ticket_assigned`
- `staff_access_denied`

Audit metadata:

- No incluye tokens.
- No incluye secretos.
- No incluye `storage_path`.
- No incluye signed URLs.
- No incluye datos bancarios completos.
- No copia cuerpos completos de mensajes o adjuntos.
