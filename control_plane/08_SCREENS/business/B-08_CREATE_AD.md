# B-08_CREATE_AD.md

SCREEN_ID: B-08_CREATE_AD
actor: business
slice: business_app
status: DRAFT_CONTROLLED

purpose:
Create ad with method/range/rate.

route:
/business/ads/create

entry points:
Dashboard

exit points:
B-09_MY_ADS

data required:
- authenticated user/session
- approved own business
- active approved business_payment_methods loaded from `GET /api/v1/business/payment-methods`
- credit wallet summary, always requiring sufficient balance; no Founder exemption
- form fields: selected approved payment method, rate_bs_per_usd, amount_min_usd, amount_max_usd
- calculated required_credits preview

endpoint used:
- GET /api/v1/business/payment-methods
- POST /api/v1/business/ads

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
Publicar anuncio

validation:
- selected payment method must come from backend-approved selector.
- no manual `payment_method_id` input.
- method/range/rate valid.
- if no approved methods exist, show empty state and block publish.

payment method selector:
- Visual selector, not free text.
- Examples:
  - Recibo Zelle → Entrego Pago Móvil Bs.
  - Recibo USDT → Entrego Pago Móvil Bs.
- Shows receive method, delivery method, delivery currency, limits and masked account when available.
- Empty state: "Aun no tienes metodos aprobados. Contacta a NODO para activar tus metodos de operacion."

permissions:
approved business

states:
- loading
- empty
- error
- offline
- forbidden
- success where applicable

disclaimer:
Los creditos son para publicar y operar anuncios dentro de NODO. No son dinero, saldo custodiado, deposito, retiro disponible ni valor transferible.

privacy:
- Show masked payment method metadata by default.
- Do not expose full account_value.
- Do not expose storage_path.
- Do not expose full bank data.
- Do not fake credit balance; if backend does not return it, show loading/empty/error.

audit events:
ad_created, ad_published, credits_held

QA checklist:
Calculates required credits
Uses selector from GET /api/v1/business/payment-methods
Does not render manual payment_method_id input
Does not publish if no approved methods exist
Does not expose account_value or storage_path

## Slice 14B1 access contract

- Requires `surface/session` allowed for `business_mini_app`.
- Requires active `business_access_links` owner link.
- Business `suspended`, `blocked`, link suspended/revoked/blocked, user restricted/blocked: do not render create action.
- Capabilities returned by backend decide whether create-ad CTA is enabled.
