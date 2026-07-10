# STATE_CONTRACT.md

## business_intake.status

- draft
- submitted
- accepted
- rejected

Post-MVP/legacy, no activo en 14D:
- under_review
- archived

## business_intake conversation state

- `last_step` guarda el paso actual del formulario guiado.
- `last_update_id` guarda el ultimo update de Telegram procesado.
- `telegram_user_id + telegram_chat_id` identifican la conversacion de intake.
- `telegram_chat_id + last_update_id` es la base de idempotencia de updates.

## support_ticket.status

- open
- waiting_user
- waiting_business
- waiting_support
- escalated
- linked_to_dispute
- resolved
- closed

## support_ticket.scope

- client_general
- order_support
- business_general
- admin_internal

## Reglas

- Soporte no cambia estados de orden.
- Chat operativo no es disputa.
- Disputa formal usa contratos de disputa.
- Intake aceptado no autoaprueba negocio sin accion admin y contrato de negocio.
- Bot intake solo acepta imagen/PDF en MVP; video queda post-MVP.
