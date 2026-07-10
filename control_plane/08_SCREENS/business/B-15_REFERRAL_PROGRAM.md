# B-15_REFERRAL_PROGRAM.md

SCREEN_ID: B-15_REFERRAL_PROGRAM
actor: business
slice: slice_08_credits_referrals
status: DRAFT_CONTROLLED

purpose:
Show referral code, referral events and earned credits cap.

route:
/business/referrals

entry points:
B-04_BUSINESS_DASHBOARD

exit points:
B-04_BUSINESS_DASHBOARD

data required:
- authenticated user/session
- `GET /api/v1/business/referrals`
- `POST /api/v1/business/referrals/apply`

read strategy:
- Read only data needed for this screen.
- Use loading skeleton.
- Use error/retry if request fails.
- Use empty state when there are no referral events.

write strategy:
- Writes only through approved API endpoints.
- No direct state transitions outside backend state machine.

Telegram UI rules:
- Use @telegram-apps/telegram-ui where possible.
- Respect themeParams.
- Use official NODO logo and tokens.
- Use MainButton only for primary CTA.

MainButton behavior:
Compartir codigo

validation:
- no self-referral
- no duplicate referral bonus
- cap 20 credits

permissions:
approved business

states:
- loading
- empty
- error
- offline
- success where applicable

audit events:
- referral_code_created
- referral_applied
- referral_bonus_granted

QA checklist:
- Shows 20 credit cap.
- Does not expose fraud/prevention internals.
- Does not promise guaranteed funds or guaranteed delivery.
