# AUDIT_EVENTS.md

Eventos obligatorios:

- job_started
- job_finished
- job_failed
- order_payment_deadline_warning_sent
- order_cancelled_payment_not_reported
- order_business_response_warning_sent
- order_disputed_business_no_payment_confirmation
- order_delivery_warning_sent
- order_disputed_business_confirmed_payment_but_not_delivered
- delivered_reminder_sent
- order_auto_completed_after_24h
- ad_expired
- founder_access_expired

Cada evento debe incluir order_id/ad_id/business_id/dispute_id cuando aplique,
estado anterior, estado nuevo, reason y `job_id`.

Audit metadata no debe contener `storage_path`, `account_value`, instrucciones
completas, signed URLs, tokens, secretos, evidencia privada ni stack traces.

`delivered_reminder_sent` debe distinguir ventana en metadata segura:

- immediate
- 12h
- 23h
