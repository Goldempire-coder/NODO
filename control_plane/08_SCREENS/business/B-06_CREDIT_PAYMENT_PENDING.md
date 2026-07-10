# B-06_CREDIT_PAYMENT_PENDING.md

SCREEN_ID: B-06_CREDIT_PAYMENT_PENDING
actor: business
slice: slice_08_credits_referrals
status: DRAFT_CONTROLLED

purpose:
Submit/track manual credit purchase proof for Zelle or USDT manual review.

route:
/business/credits/pending

entry points:
B-05_BUY_CREDITS

exit points:
B-07_MY_CREDITS_LEDGER

data required:
- authenticated user/session
- credit_purchase from `credit_purchases`
- package_code
- payment_method
- status
- manual payment instructions
- proof metadata from `file_assets` without `storage_path`

read strategy:
- Read only data needed for this screen.
- Use loading skeleton.
- Use error/retry if request fails.
- Use empty state when no manual payment is pending.

write strategy:
- Manual proof is submitted only through `POST /api/v1/business/credits/manual-payment`.
- Proof must use `file_assets.resource_type = credit_purchase` and `file_type = credit_purchase_proof`.
- No direct state transitions outside backend state machine.

Telegram UI rules:
- Use @telegram-apps/telegram-ui where possible.
- Respect themeParams.
- Use official NODO logo and tokens.
- Use MainButton only for primary CTA.

MainButton behavior:
Enviar comprobante

validation:
- proof required for Zelle manual submission
- TxID/hash required for USDT manual submission when applicable
- status must be `pending_manual_review`
- `storage_path` must never be shown

permissions:
approved business

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
- manual_credit_payment_submitted

QA checklist:
- pending_manual_review state is clear.
- does not show Stripe purchases as manual pending proof.
- cannot submit proof for paid/approved/rejected purchase.
- no `storage_path` appears in UI.
