# B-07_MY_CREDITS_LEDGER.md

SCREEN_ID: B-07_MY_CREDITS_LEDGER
actor: business
slice: slice_08_credits_referrals
status: DRAFT_CONTROLLED

purpose:
Show own credit wallet and ledger.

route:
/business/credits

entry points:
B-04_BUSINESS_DASHBOARD

exit points:
B-05_BUY_CREDITS

data required:
- authenticated user/session
- `GET /api/v1/business/credits/wallet`
- `GET /api/v1/business/credits/ledger`

read strategy:
- Read only data needed for this screen.
- Use loading skeleton.
- Use error/retry if request fails.
- Use empty state when ledger is empty.

write strategy:
- Writes only through approved API endpoints.
- No direct state transitions outside backend state machine.

Telegram UI rules:
- Use @telegram-apps/telegram-ui where possible.
- Respect themeParams.
- Use official NODO logo and tokens.
- Use MainButton only for primary CTA.

MainButton behavior:
Comprar creditos

validation:
none

permissions:
approved business

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
none

QA checklist:
- Shows available/blocked/consumed.
- Only shows own wallet/ledger.
- Does not show Stripe secrets or proof storage data.
