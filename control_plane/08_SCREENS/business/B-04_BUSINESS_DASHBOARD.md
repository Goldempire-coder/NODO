# B-04_BUSINESS_DASHBOARD.md

SCREEN_ID: B-04_BUSINESS_DASHBOARD
actor: business
slice: slice_08_credits_referrals
status: DRAFT_CONTROLLED

purpose:
Business overview with credits summary, founder status and entry points.

route:
/business

entry points:
Approved business

exit points:
B-05_BUY_CREDITS, B-07_MY_CREDITS_LEDGER, B-08_CREATE_AD, B-11_INCOMING_ORDERS, B-15_REFERRAL_PROGRAM

data required:
- authenticated user/session
- approved business profile
- `GET /api/v1/business/credits/wallet`
- credit summary/founder status/referral entry metadata

read strategy:
- Read only data needed for this screen.
- Use loading skeleton.
- Use error/retry if request fails.
- Use empty state when list is empty.

write strategy:
- Writes only through approved API endpoints.
- No direct state transitions outside backend state machine.

Telegram UI rules:
- Use @telegram-apps/telegram-ui where possible.
- Respect themeParams.
- Use official NODO logo and tokens.
- Use MainButton only for primary CTA.

MainButton behavior:
Contextual

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
- Shows credits/trust/rating.
- Shows founder access status when present.
- Does not promise escrow, guaranteed funds or guaranteed delivery.

## Slice 14B1 access contract

- Screen only renders after `GET /api/v1/surface/session` allows `business_mini_app`.
- If `access_state` is not `allowed`, render the governed access state from `BUSINESS_MINI_APP_SURFACE.md`.
- Do not use `/api/v1/businesses/me` as the authorization gate.
