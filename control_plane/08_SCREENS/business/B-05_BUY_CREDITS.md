# B-05_BUY_CREDITS.md

SCREEN_ID: B-05_BUY_CREDITS
actor: business
slice: slice_08_credits_referrals
status: DRAFT_CONTROLLED

purpose:
Choose credit package and start Base USDC on-chain purchase, or fallback Stripe/manual if enabled by backend.

route:
/business/credits/buy

entry points:
B-04_BUSINESS_DASHBOARD

exit points:
B-06_CREDIT_PAYMENT_PENDING, B-07_MY_CREDITS_LEDGER

data required:
- authenticated user/session
- approved business
- credit packages from `CREDITS_API.md`

read strategy:
- Read only data needed for this screen.
- Use loading skeleton.
- Use error/retry if request fails.
- Use empty state when packages are unavailable.

write strategy:
- Base USDC writes through `POST /api/v1/business/credits/base-payment`.
- Stripe checkout writes through `POST /api/v1/business/credits/stripe-checkout`.
- Manual payment writes through `POST /api/v1/business/credits/manual-payment`.
- No frontend redirect may credit wallet.
- No frontend on-chain status may credit wallet.
- No direct state transitions outside backend state machine.

Telegram UI rules:
- Use @telegram-apps/telegram-ui where possible.
- Respect themeParams.
- Use official NODO logo and tokens.
- Use MainButton only for primary CTA.

MainButton behavior:
Comprar paquete

validation:
- package valid
- payment method valid; primary MVP on-chain method is `base_usdc_onchain`
- USDT Base is not selectable in MVP
- Idempotency-Key required for purchase creation

permissions:
approved business

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
- credit_purchase_created
- onchain_credit_purchase_created when Base USDC selected
- stripe_checkout_started when Stripe selected
- manual_credit_payment_submitted when manual selected

QA checklist:
- Shows packages.
- Stripe redirect does not display credited balance until webhook confirms.
- Copy does not promise escrow, guaranteed funds or guaranteed delivery.
- Base USDC screen shows Base network, USDC contract, exact amount, destination wallet and expiration.
- Does not show private keys, seed phrases, RPC internals or anonymity/evasion copy.
