# SCOPE.md

## Objective

Chat por orden, adjuntos privados y apertura de disputas con evidencia basica.

Slice 07 no cierra ordenes, no confirma recepcion del remitente, no califica
negocios y no resuelve disputas con efectos financieros/admin.

## Included

- messages
- message_attachments
- disputes
- dispute_events
- orders
- audit_logs
- GET /api/v1/orders/{id}/messages
- POST /api/v1/orders/{id}/messages
- POST /api/v1/orders/{id}/message-attachments
- POST /api/v1/orders/{id}/disputes
- GET /api/v1/admin/disputes
- GET /api/v1/admin/disputes/{id}

## Affected screens

- R-09_ORDER_TRACKING_CHAT
- B-13_BUSINESS_CHAT

## Explicitly excluded

- payment processing
- business verification
- credit purchase
- R-10_CONFIRM_RECEIVED
- R-11_RATING
- A-06_DISPUTES_LIST
- A-07_DISPUTE_DETAIL
- remitter receipt confirmation
- order completion
- ratings
- auto-complete
- admin dispute resolution
- credit release/consume/adjustment from dispute resolution
- changing `ad.status` from dispute resolution
- jobs masivos

If a requested change falls outside this scope, stop and report BLOCKED_BY_MISSING_CONTRACT or request owner approval.
