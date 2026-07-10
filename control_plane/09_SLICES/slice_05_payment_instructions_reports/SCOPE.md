# SCOPE.md

## Objective

Mostrar instrucciones completas de pago al remitente dueno y permitir que el remitente reporte pago con evidencia privada.

## Included

- reveal controlado de instrucciones completas
- tracking de `orders.payment_data_revealed_at`
- tracking de `orders.payment_data_revealed_by`
- reporte de pago del remitente
- evidencia privada de pago usando `file_assets`
- transicion `waiting_payment -> payment_reported`
- `payment_reports`
- `file_assets` para `payment_evidence`
- `orders`
- `order_state_events`
- `audit_logs`
- `GET /api/v1/orders/{id}/payment-instructions`
- `POST /api/v1/orders/{id}/payment-report`
- `POST /api/v1/orders/{id}/payment-evidence`

## Affected screens

- R-07_PAYMENT_INSTRUCTIONS
- R-08_REPORT_PAYMENT

## Explicitly excluded

- business confirms/rejects payment
- delivery/pago movil
- chat
- disputes
- massive jobs
- credit consumption
- real credit purchase/accreditation
- admin override
- R-09_ORDER_TRACKING_CHAT except link/state toward slice 07

## Explicit non-entities

- Do not create `payment_evidence_files`.
- Do not create `storage_objects`.
- Use `file_assets` for payment evidence.

If a requested change falls outside this scope, stop and report `BLOCKED_BY_SCOPE_EXPANSION` or request owner approval.
