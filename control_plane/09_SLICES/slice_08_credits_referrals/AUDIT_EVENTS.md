# AUDIT_EVENTS.md

Eventos requeridos:

- credit_purchase_created
- stripe_checkout_started
- stripe_payment_succeeded
- stripe_payment_failed
- manual_credit_payment_submitted
- manual_credit_payment_approved
- manual_credit_payment_rejected
- credits_added
- credits_held
- credits_released
- credits_consumed
- admin_credit_adjustment
- founder_access_granted
- founder_access_expired
- founder_access_revoked
- founder_free_use
- referral_code_created
- referral_code_applied
- referral_bonus_awarded
- referral_rejected

Audit rules:

- Include actor_user_id, actor_role, resource_type, resource_id, old/new state
  where applicable, reason, request_id/job_id and timestamp.
- Admin sensitive actions require reason.
- Audit logs are append-only.
- No Stripe secrets, signed URLs, full proof data, `storage_path` or private
  payment data in audit metadata.
