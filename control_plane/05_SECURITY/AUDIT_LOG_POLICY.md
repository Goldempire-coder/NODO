# AUDIT_LOG_POLICY.md

## Slice 14 audit events

Events:
- business_intake_started
- business_intake_contact_shared
- business_intake_step_answered
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
- business_suspended
- business_reactivated
- business_blocked
- support_ticket_created
- support_message_created
- support_ticket_escalated
- support_ticket_linked_to_dispute
- support_ticket_resolved
- support_ticket_closed
- admin_operational_search_performed
- staff_invite_created
- staff_invite_expired
- staff_activated
- staff_suspended
- staff_revoked
- staff_permissions_updated
- staff_activity_viewed
- staff_ticket_assigned
- staff_access_denied
- surface_access_denied

Audit payloads must not include raw documents, full support messages, storage paths, signed URLs, tokens, secrets, account values or private evidence.

Contrato de auditoria append-only.

## Objetivo

Toda accion sensible debe dejar evidencia tecnica suficiente para investigar abusos, errores, disputas y cambios de estado.

## Regla madre

Los audit logs son append-only. No se actualizan ni borran desde flujos normales.

## Campos minimos

```txt
id
event_type
actor_user_id
actor_role
resource_type
resource_id
action
old_value
new_value
reason
request_id
ip_hash
user_agent
created_at
metadata
```

## Eventos obligatorios

- auth login/session issue
- business submitted/approved/rejected/suspended
- ad created/paused/archived/expired
- credits blocked/released/consumed/adjusted
- Stripe checkout created
- Stripe webhook received/succeeded/failed
- manual credit payment submitted/approved/rejected
- order created/cancelled/payment_reported/payment_confirmed/delivered/completed/disputed
- payment evidence uploaded/revealed
- dispute opened/resolved
- admin action executed
- sensitive data viewed
- admin_order_chat_viewed
- admin_operational_search_performed

`admin_order_chat_viewed` registra actor, `order_id`, cantidad de mensajes,
direccion de pagina y si un highlight solicitado fue encontrado. Nunca registra
el cuerpo del chat, metadata privada de adjuntos, `storage_path` ni signed URLs.

`admin_operational_search_performed` registra hash corto de la busqueda
normalizada, largo, limite y conteos por grupo. Nunca registra el texto crudo
de la busqueda, IDs de resultados, cuerpos de mensajes ni datos privados.

## Datos prohibidos en audit log

- tokens
- secretos
- comprobantes completos
- datos bancarios completos
- private storage keys
- JWT
- bot token
- Stripe raw secret headers

## Integridad

- Cada request mutante debe tener `request_id`.
- Eventos duplicables deben incluir idempotency key cuando aplique.
- Webhooks deben registrar provider event id.
- Errores de auditoria en acciones criticas deben bloquear la accion, no ignorarse silenciosamente.

## Tests obligatorios

- accion sensible genera audit log.
- audit log no contiene secretos.
- old/new value se guarda en cambios admin.
- webhooks repetidos no duplican efectos, pero quedan auditados.
- intento no autorizado importante queda registrado cuando aplique.

## Bloqueo

Si una feature sensible no puede auditarse, Builder debe reportar:

```txt
BLOCKED_BY_SECURITY_GAP
```

## Audit vs Observability - slice 24

Audit formal and observability are separate:

- audit formal is durable and records sensitive actions, state changes, actors and reasons;
- observability is operational diagnostics with TTL, sampling and redaction;
- audit must not store session replay payloads;
- observability must not be used as financial ledger or compliance source of truth.

Audit events required for observability admin access:

- `observability_events_viewed`
- `observability_session_viewed`
- `observability_export_created`
- `observability_retention_cleanup_run`
- `observability_access_denied`
- `observability_config_changed`

Ingesting every breadcrumb must not create audit spam.
