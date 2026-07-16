# AUDIT_EVENTS.md

Eventos:
- `support_ticket_created`
- `support_message_created`
- `support_attachment_uploaded`
- `support_attachment_viewed`
- `support_ticket_assigned`
- `support_ticket_escalated`
- `support_ticket_linked_to_dispute`
- `support_ticket_resolved`
- `support_ticket_closed`

Audit no debe incluir:
- body completo;
- `storage_path`;
- signed URL;
- tokens;
- secretos;
- `account_value`;
- datos bancarios completos;
- evidencia privada completa.
