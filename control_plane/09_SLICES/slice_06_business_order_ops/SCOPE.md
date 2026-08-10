# SCOPE.md

## Objective

Permitir al negocio revisar ordenes, confirmar pagos y marcar pago movil
enviado. La decision C0 posterior sustituye el rechazo directo por apertura de
disputa.

## Included

- listado de ordenes del negocio
- detalle de orden del negocio
- confirmar pago recibido
- reportar problema con pago mediante disputa
- marcar pago movil enviado/entregado
- consumo de creditos al confirmar pago
- `orders`
- `payment_reports`
- `ads`
- `order_state_events`
- `credits_ledger`
- `credit_wallets`
- `audit_logs`
- `GET /api/v1/business/orders`
- `GET /api/v1/business/orders/{id}`
- `POST /api/v1/business/orders/{id}/confirm-payment`
- `POST /api/v1/orders/{id}/disputes`
- `POST /api/v1/business/orders/{id}/reject-payment-report` solo como ruta
  legacy que no debe mutar
- `POST /api/v1/business/orders/{id}/mark-delivered`

## Affected screens

- `B-11_INCOMING_ORDERS`
- `B-12_BUSINESS_ORDER_DETAIL`

## Explicitly excluded

- chat
- resolucion de disputas; la apertura por problema con pago se incorpora por C0
- confirmacion de recibido por remitente
- auto-complete
- jobs masivos
- admin override
- credit purchases
- compra/acreditacion real de creditos
- republicar o reactivar el anuncio archivado
- marketplace ranking
- `B-13_BUSINESS_CHAT`, salvo link/estado hacia slice 07
- `R-09_ORDER_TRACKING_CHAT`
- `R-10_CONFIRM_RECEIVED`

If a requested change falls outside this scope, stop and report `BLOCKED_BY_SCOPE_EXPANSION` or request owner approval.
