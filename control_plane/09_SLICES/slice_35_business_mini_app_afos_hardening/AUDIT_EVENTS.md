# AUDIT_EVENTS.md

## Eventos backend esperados

Business:

- `business_accepting_orders_updated`
- `business_pin_set`
- `business_pin_verified`
- `business_pin_failed`
- `business_pin_locked`
- `business_payment_method_self_added`
- `business_payment_method_self_updated`
- `business_payment_method_self_deleted`

Ads:

- `ad_created`
- `ad_published`
- `ad_updated`
- `ad_paused`
- `ad_reactivated`
- `ad_archived`
- `ad_republished`
- `ad_expired`
- `credits_held`
- `credits_consumed`

Credits:

- `onchain_credit_purchase_created`
- `onchain_credit_purchase_tx_submitted`
- `onchain_credit_purchase_credited`
- `onchain_credit_purchase_rejected`
- `credits_added`

Orders:

- `order_created`
- `payment_reported`
- `payment_confirmed`
- `payment_report_rejected`
- `order_delivered`
- `order_auto_completed_after_24h`
- dispute/support events when used.

Frontend breadcrumbs:

- `screen_view`
- `action_started`
- `action_completed`
- `action_failed`
- `api_failure`
- `slow_screen_transition`
- `slow_sensitive_action`

## Reglas

- Eventos de auditoria no deben incluir PIN, token, Zelle completo, wallet privada, seed phrase, tx hash completo ni signed URL.
- Eventos de frontend pueden incluir route template y error code.
- Eventos de backend deben incluir request id cuando este disponible.
- Acciones financieras deben poder reconstruirse con audit log + ledger + order state events.

## Evidencia

- tests de eventos obligatorios;
- scan de metadata sensible;
- reporte builder con eventos agregados o validados.
