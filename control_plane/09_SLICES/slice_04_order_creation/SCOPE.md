# SCOPE.md

## Objective

Crear orden con snapshot inmutable de anuncio, tasa, limites, instrucciones y timer waiting_payment.

## Included

- orders
- order_state_events
- ads
- audit_logs
- orders.idempotency_key
- POST /api/v1/orders
- GET /api/v1/orders/{id}
- GET /api/v1/orders/mine
- POST /api/v1/orders/{id}/extend-payment-deadline
- POST /api/v1/orders/{id}/cancel

## Affected screens

- R-05_CREATE_ORDER
- R-06_ORDER_SUMMARY
- R-12_MY_ORDERS

## Explicitly excluded

- payment evidence upload
- business confirm payment
- delivery
- disputes

If a requested change falls outside this scope, stop and report BLOCKED_BY_MISSING_CONTRACT or request owner approval.
