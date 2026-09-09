# App cliente - pilot gate read-only review

Status: READ_ONLY_MAP_COMPLETED
Date: 2026-09-09
Scope: Cliente Telegram Mini App, supporting backend endpoints, legal/copy posture, pagination/cost behavior, and pilot readiness.
Product code changes: none.

## Executive verdict

The cliente app is acceptable with concerns for a controlled pilot, assuming the pilot stays small, invited, and manually supervised.

I would not call it production-clean yet. The main remaining issues are not core order/payment logic breakage; they are legal-language cleanup, stale tests, terms-version governance, and a few cost controls that should be tightened before scale.

## What exists today

The cliente app has these mapped surfaces:

- `welcome`
- `terms`
- `client-profile-setup`
- `profile`
- `marketplace-search`
- `marketplace-list`
- `marketplace-detail`
- `create-order`
- `order-summary`
- `report-payment`
- `my-orders`
- `messages`
- `order-chat`
- `support`

Primary evidence:

- `apps/web/src/constants/clientViews.ts`
- `apps/web/src/hooks/workspace/useClientNavigationState.ts`
- `apps/web/src/screens/client/ClientWorkspaceShell.tsx`

## What is good

1. The app now avoids the old risky public language such as "cambiar", "cuanto vas a enviar", "negocio verificado", "dinero protegido", "escrow", and similar claims in the main visible cliente screens.

2. The current marketplace copy uses safer framing:

- "Directorio de ofertas"
- "Que monto buscas?"
- "Elige un metodo publicado"
- "Entrega publicada"
- "Ofertas disponibles"
- "condiciones publicadas"
- "Coordina los detalles directamente con el negocio"

Evidence:

- `apps/web/src/screens/client/ClientMarketplaceScreens.tsx:73`
- `apps/web/src/screens/client/ClientMarketplaceScreens.tsx:74`
- `apps/web/src/screens/client/ClientMarketplaceScreens.tsx:98`
- `apps/web/src/screens/client/ClientMarketplaceScreens.tsx:118`
- `apps/web/src/screens/client/ClientMarketplaceScreens.tsx:127`
- `apps/web/src/screens/client/ClientMarketplaceScreens.tsx:128`

3. Terms/profile copy is aligned with the current no-custody posture:

- NODO is presented as a directory of registered businesses.
- The user chooses the business and coordinates directly.
- NODO records order/evidence for support/audit.
- NODO says it does not receive or retain funds.

Evidence:

- `apps/web/src/screens/client/ClientOnboardingScreens.tsx`
- `apps/web/src/constants/legal.ts`
- `apps/api/app/modules/users/terms.py`

4. Marketplace access is restricted to active remitter users, and marketplace listings filter out inactive, expired, unapproved, high-risk, paused, over-capacity, or inactive-payment-method ads.

Evidence:

- `apps/api/app/modules/ads/policy.py`
- `apps/api/app/modules/ads/marketplace.py`
- `apps/api/app/modules/ads/postgres_repository.py`

5. Order creation revalidates backend state before creating an order. It does not trust only what the frontend selected.

Evidence:

- `apps/api/app/modules/orders/remitter_routes.py`
- `apps/api/app/modules/orders/create_order_flow.py`

6. Conversations are not loaded on app open. They load when the user enters chat or support, and older messages use explicit pagination.

Evidence:

- `apps/api/app/modules/chat/routes.py`
- `apps/web/src/hooks/workspace/useClientChatDisputesModel.ts`
- `apps/web/src/screens/client/ClientOrderChatScreen.tsx`
- `apps/web/src/screens/support/SurfaceSupportPrimitives.tsx`

7. Support visibility is scoped by requester/business/admin rules. Non-admin support messages filter internal visibility.

Evidence:

- `apps/api/app/modules/support/service.py`
- `apps/api/app/modules/support/postgres_repository.py`

8. Attention alerts have visibility and backoff guards. The browser does not keep polling the same way when the document is hidden.

Evidence:

- `apps/web/src/hooks/useSurfaceAttentionModel.ts:14`
- `apps/web/src/hooks/useSurfaceAttentionModel.ts:93`
- `apps/web/src/hooks/useSurfaceAttentionModel.ts:110`
- `apps/web/src/hooks/useSurfaceAttentionModel.ts:118`

## Findings

### P1 - Terms version was not bumped after legal-language changes

Frontend and backend still use terms version `2026-07-06`.

If the safer legal language is considered a material change, users who already accepted the old version will not be forced to accept the corrected posture again.

Evidence:

- `apps/web/src/constants/legal.ts`
- `apps/api/app/modules/users/terms.py`

Recommended fix:

- Bump frontend and backend terms version.
- Update tests.
- Force reacceptance only for cliente users before pilot, if owner wants the corrected posture acknowledged.

### P1 - Backend chat system messages still use older/riskier wording

Visible screens were cleaned, but backend-generated chat/system messages still contain wording like:

- "Negociacion creada"
- "No envies el pago"
- "Cliente marco Pago enviado"
- "Negocio marco Pago Movil enviado"
- "Negociacion completada"
- "antes de enviar"

This does not necessarily break logic, but the wording is less aligned with the no-custody/no-remittance posture.

Evidence:

- `apps/api/app/modules/chat/service.py:28`
- `apps/api/app/modules/chat/service.py:29`
- `apps/api/app/modules/chat/service.py:223`
- `apps/api/app/modules/chat/service.py:263`
- `apps/api/app/modules/chat/service.py:276`
- `apps/api/app/modules/chat/service.py:284`
- `apps/api/app/modules/chat/service.py:585`

Recommended fix:

- Change these strings only.
- Use wording like "solicitud", "orden", "pago directo al negocio", "reporte de pago", "entrega marcada", and "realizar pago directo".
- Do not touch status names, order logic, payment confirmation logic, credits, or backend state transitions.

### P2 - Static tests now contradict the current safer UI copy

Some tests still expect old phrases that were already removed from the UI, including:

- "Cuanto vas a enviar?"
- "Indica el monto que vas a enviar."
- "Reportar operacion"
- "Reporte recibido... operacion"

That means CI can fail or, worse, future agents can accidentally reintroduce older wording to satisfy stale tests.

Evidence:

- `apps/api/tests/test_client_marketplace_copy_static.py:57`
- `apps/api/tests/test_client_marketplace_copy_static.py:74`
- `apps/api/tests/test_client_operation_report_static.py:18`
- `apps/api/tests/test_client_operation_report_static.py:19`

Recommended fix:

- Update tests to match current approved copy.
- Keep forbidden-language assertions.
- Add assertions for the corrected backend chat/system messages.

### P2 - Marketplace cache still revalidates even when fresh

The cliente app shows cached marketplace results for speed, but it still performs a network request even when the cache is fresh.

This is safer for freshness, but it costs more API/database usage than necessary.

Evidence:

- `apps/web/src/hooks/workspace/useClientMarketplaceModel.ts:81`
- `apps/web/src/hooks/workspace/useClientMarketplaceModel.ts:87`
- `apps/web/src/hooks/workspace/useClientMarketplaceModel.ts:188`
- `apps/web/src/hooks/workspace/useClientMarketplaceModel.ts:204`

Recommended fix:

- For pilot cost control, return early when the 30-second cache is fresh.
- Keep explicit search/refresh as a real fetch.
- Update the existing static test that currently expects the stale-while-revalidate behavior.

### P2 - Support client loads a larger first page than needed

The shared support model requests up to 50 tickets. For the small pilot this is fine, but for scale this should probably be 20 or 25.

Evidence:

- `apps/web/src/hooks/useSurfaceSupportModel.ts`
- `apps/api/app/modules/support/routes.py`

Recommended fix:

- Lower the default client-side support inbox page size.
- Keep "Cargar mas" for older tickets.

### P3 - Active chat polling is acceptable for pilot, but should back off later

The order chat refreshes every 5 seconds while the chat view is active and visible. It does not load all conversations globally, which is good.

For scale, polling should eventually use backoff, latest-message cursors, or server push.

Evidence:

- `apps/web/src/hooks/workspace/useClientOrderChatSync.ts`
- `apps/web/src/hooks/workspace/useClientChatDisputesModel.ts`

Recommended fix:

- Not urgent for small pilot.
- Revisit before wider rollout.

### P3 - Messages tab uses orders as the conversation index

The messages screen currently uses the user's orders as the list of conversations. That avoids loading all chat bodies, but still couples "messages" to the order list.

Evidence:

- `apps/web/src/screens/client/ClientOrderScreens.tsx`
- `apps/web/src/hooks/workspace/useRemitterOrdersModel.ts`

Recommended fix:

- Pilot: acceptable.
- Later: add a lightweight conversation index endpoint with last message, unread/attention state, and cursor.

### P3 - Prior "No tienes permiso" screenshot needs live Telegram verification

The current client error mapper should convert 403/SURFACE_ACCESS_DENIED into friendlier language, but user screenshots previously showed "No tienes permiso para realizar esta accion."

Evidence:

- `apps/web/src/hooks/useClientWorkspaceModel.ts`
- User Telegram screenshots during staging checks.

Recommended fix:

- Verify the current deployed Telegram version after the next web deploy.
- If the generic message still appears, map that exact backend error path to the client-friendly copy.

### P3 - Sort names accept trust/speed even though ranking is neutral

Backend accepts `trust`, `rate`, and `speed`, but public ranking currently sorts by rate, creation time, and id.

This is okay if those choices are not exposed as claims. If exposed later, the label should not imply endorsement or a hidden advantage.

Evidence:

- `apps/api/app/modules/ads/marketplace.py`
- `apps/api/app/modules/ads/postgres_repository.py`

Recommended fix:

- Keep UI copy neutral.
- If sort controls are added, name them honestly: "mejor referencia", "recientes", etc.

## Recommended next work

1. Text-only legal cleanup in backend chat/system strings and operation-report labels.

2. Terms-version decision:

- If Carlos wants every client to accept corrected terms before pilot, bump version now.
- If pilot is invite-only and existing testers are known, document that current users already saw/accepted the corrected flow manually.

3. Update stale static tests so CI protects the new safer language.

4. Cost patch:

- Marketplace: use fresh cache without immediate refetch.
- Support inbox: lower first page size from 50 to 20 or 25.
- Keep explicit "Cargar mas" behavior.

5. Live Telegram validation after deploy:

- Inicio
- Negocios
- Ordenes
- Mensajes
- Perfil
- Terminos
- Crear solicitud
- Reportar pago directo
- Chat de orden
- Soporte

## Pilot readiness

Recommended status: ACCEPTABLE_WITH_CONCERNS_FOR_CONTROLLED_PILOT.

Conditions:

- Keep USDC credit purchases out of real-money production until explicitly approved.
- Use manual credit assignment for pilot if needed.
- Keep pilot invite-only.
- Keep emergency mode/kill switch tested.
- Keep Telegram admin alerts monitored.
- Do not market NODO as exchange, remittance, custody, escrow, guaranteed protection, or verified financial service.

## Verification performed

Performed:

- Static read of cliente screens.
- Static read of cliente hooks.
- Static read of marketplace/order/chat/support/attention backend paths.
- Static read of current tests related to cliente copy.
- Static read of control-plane legal posture.

Not performed:

- No code edits to product files.
- No tests run.
- No staging deploy.
- No live Telegram browser/device verification in this pass.
