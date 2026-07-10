# AUDIT_EVENTS.md

## Eventos canonicos

- business_intake_started
- business_intake_submitted
- business_intake_document_uploaded
- business_intake_viewed_by_admin
- business_intake_accepted
- business_intake_rejected
- business_created_from_intake
- business_access_linked
- business_access_unlinked
- business_access_suspended
- business_access_reactivated
- business_access_blocked
- business_telegram_linked (legacy alias; no usar como evento canonico nuevo)
- support_ticket_created
- support_message_created
- support_ticket_escalated
- support_ticket_linked_to_dispute
- support_ticket_resolved
- support_ticket_closed
- surface_access_denied

Audit no debe contener documentos completos, storage paths, tokens, secretos ni datos bancarios completos.
