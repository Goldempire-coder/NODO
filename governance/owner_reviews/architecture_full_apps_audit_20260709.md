# Full Apps Architecture Audit

Status: ARCHITECTURE_AUDIT_COMPLETED_WITH_REPAIRS_RECOMMENDED

Scope:

- `apps/web`
- `apps/api`
- `scripts`
- surface boundaries: client mini app, business mini app, admin web, business intake bot

No implementation code was changed in this audit.

## Executive Result

The project is not in a broken architecture state.

The main surfaces are now separated:

- Client Mini App exists separately.
- Business Mini App exists separately.
- Admin Web exists separately.
- Business intake bot is backend-only and separated from the client bot token/webhook.

However, there are still important cleanup targets before calling the architecture clean enough to scale comfortably.

The biggest remaining risks are:

1. Client UI screen monolith: `RemitterScreens.tsx`.
2. Backend order service orchestration: `orders/service.py`.
3. Backend credit approval transaction: `credits/repository.py`.
4. Backend business intake bot state machine: `business_intake/service.py`.
5. Global CSS is large and mixes all surfaces.

## Frontend Surface Audit

### Client Mini App

Main issue:

- `apps/web/src/screens/client/RemitterScreens.tsx`
- Size: 906 lines by Python `splitlines`.
- Contains one large exported component with many `view === ...` blocks.

Views inside the same component include:

- `welcome`
- `terms`
- `client-profile-setup`
- `profile`
- `marketplace-search`
- `marketplace-list`
- `marketplace-detail`
- `create-order`
- `order-summary`
- `payment-instructions`
- `report-payment`
- `my-orders`
- `messages`

Assessment:

This is the strongest frontend architecture issue remaining. The client model is split, but the screen renderer is still too large. This is a real cleanup target.

Recommended cut:

Create separate files:

- `WelcomeScreen.tsx`
- `TermsScreen.tsx`
- `ClientProfileSetupScreen.tsx`
- `ClientProfileScreen.tsx`
- `MarketplaceSearchScreen.tsx`
- `MarketplaceListScreen.tsx`
- `MarketplaceDetailScreen.tsx`
- `CreateOrderScreen.tsx`
- `OrderSummaryScreen.tsx`
- `PaymentInstructionsScreen.tsx`
- `ReportPaymentScreen.tsx`
- `MyOrdersScreen.tsx`
- `MessagesScreen.tsx`

Keep `RemitterScreens.tsx` only as a small router.

Priority: HIGH.

### Business Mini App

Result: acceptable.

Important files:

- `useBusinessMiniAppModel.ts`: 80 lines
- `useBusinessAccessModel.ts`: 81 lines
- `useBusinessAdsModel.ts`: 94 lines
- `useBusinessOrdersModel.ts`: 78 lines
- `useBusinessCreditsModel.ts`: 152 lines
- `useBusinessChatModel.ts`: 123 lines
- `useBusinessTelegramControls.ts`: 65 lines

Boundary scan result:

```txt
BUSINESS_APP_BOUNDARY_SCAN_OK
```

No findings for:

- client imports
- admin imports
- verification screens
- `/api/v1/businesses/me` as gate
- `/api/v1/admin`
- `account_value`
- `storage_path`
- prohibited claims

Assessment:

Business Mini App architecture is currently healthy. It needs UX polish, not structural repair.

Priority: LOW for architecture, MEDIUM for UX polish.

### Admin Web

Result: acceptable after recent cuts.

Main model:

- `useAdminWebModel.ts`: 221 lines
- mostly composer now

Screen file:

- `AdminWebScreens.tsx`: 526 lines
- Internally split into many small functions.
- Largest detected screen subfunction: `BusinessIntakeDetail`, 57 lines.

Assessment:

`AdminWebScreens.tsx` is large as a file, but not a severe Frankenstein because it is internally split into small components. It can be split later by admin domain, but this is not the next highest-risk cut.

Priority: MEDIUM/LOW.

### Global CSS

File:

- `apps/web/src/app/globals.css`
- Size: 1207 lines.

Assessment:

This file mixes base styles, client mini app, business mini app and admin web styles. It is not a logic bug, but it is a maintainability risk.

Recommended future split:

- `globals.css` for base tokens/reset only.
- `client.css`
- `business.css`
- `admin-web.css`

Priority: MEDIUM.

## Backend Module Audit

### Orders

Files:

- `apps/api/app/modules/orders/service.py`: 951 lines
- `apps/api/app/modules/orders/repository.py`: 776 lines

Long runtime functions:

- `create_order`: 123 lines
- nested `compute` inside `create_order`: 110 lines
- `confirm_business_payment`: 104 lines
- nested `compute` inside `confirm_business_payment`: 85 lines
- `report_payment`: 95 lines
- `upload_payment_evidence`: 83 lines

Assessment:

This is a real backend cleanup target. The service is doing validation, state transitions, repository orchestration, audit payloads, idempotency and response shaping in large methods.

Recommended cuts:

1. Extract order creation helper/use case:
   - validate idempotency payload
   - validate ad/business/payment method
   - build order create fields
   - write audit/state events

2. Extract payment report helper/use case:
   - method-specific validation
   - evidence handling
   - state transition response

3. Extract business confirmation helper:
   - atomic repository call remains
   - audit event building separated
   - response shaping separated

Priority: HIGH.

### Credits

File:

- `apps/api/app/modules/credits/repository.py`: 813 lines.

Long runtime function:

- `PostgresCreditRepository.approve_purchase`: 181 lines.

Assessment:

This function mixes:

- purchase row locking
- wallet creation/update
- purchase approval
- ledger insertion
- referral lookup
- referral bonus wallet update
- referral event mutation
- rejection when referral cap reached

This is too much for one repository method.

Recommended cut:

- Keep one transaction boundary, but split private helpers:
  - `_lock_purchase_for_approval`
  - `_ensure_credit_wallet`
  - `_insert_purchase_ledger`
  - `_grant_referral_bonus_if_eligible_pg`
  - `_reject_referral_bonus_if_cap_reached`

Priority: HIGH.

### Business Intake Bot

File:

- `apps/api/app/modules/business_intake/service.py`: 784 lines.

Long runtime functions:

- `process_telegram_update`: 111 lines
- `_handle_text_step`: 90 lines
- `_admin_review`: 81 lines

Assessment:

This area deserves cleanup because the bot has already shown real conversational edge cases. The current implementation is understandable, but the state machine is too concentrated in one service.

Recommended cut:

- Extract conversation state handling:
  - `BusinessIntakeConversationHandler`
  - `parse_update_context`
  - `handle_start`
  - `handle_file`
  - `handle_text_step`
  - `handle_finalizar`

Also recommended:

- Add a small table or update log if duplicate media groups continue causing repeated prompts.

Priority: HIGH.

### Jobs Worker

File:

- `apps/api/app/modules/jobs/worker.py`: 648 lines.

Long functions:

- `run`: 109 lines
- `_open_dispute`: 69 lines
- `_handle_delivered`: 68 lines

Assessment:

The worker is large but already split by order/ad/founder handling. It is less urgent than orders, credits and bot state machine.

Recommended future cut:

- split worker handlers into:
  - `OrderExpirationHandler`
  - `AdExpirationHandler`
  - `FounderExpirationHandler`
  - `NotificationScheduler`

Priority: MEDIUM.

### Ads

File:

- `apps/api/app/modules/ads/service.py`: 487 lines.

Long functions:

- `create_ad`: 115 lines
- nested `compute`: 96 lines
- `search`: 78 lines

Assessment:

This is moderately large but not the worst offender. `create_ad` could be split after orders/credits/bot cleanup.

Priority: MEDIUM.

## API Wrapper Audit

Frontend API wrappers exist by domain:

- `admin.ts`
- `ads.ts`
- `businessAds.ts`
- `businesses.ts`
- `businessOrders.ts`
- `chat.ts`
- `credits.ts`
- `orders.ts`
- `paymentReports.ts`
- `surface.ts`
- `users.ts`

Assessment:

This is good. Components are not building raw API routes directly except through wrappers.

Priority: OK.

## Surface Boundary Audit

Business Mini App:

- clean boundary
- no client/admin imports found

Admin Web:

- separated shell/model
- no Telegram MainButton/themeParams dependency found in admin surface after previous refactor

Client:

- model hooks are split
- screen renderer remains too large

Business Intake Bot:

- separated token/webhook exists
- service state machine still too concentrated

## Recommended Repair Order

### Cut 1: Client screen split

Reason:

This is the clearest frontend Frankenstein left. It affects maintainability and visual iteration speed.

Target:

- `apps/web/src/screens/client/RemitterScreens.tsx`

Goal:

- Make it a small router.
- Move each major view to its own screen file.
- Preserve copy, layout, handlers and endpoints.

### Cut 2: Business intake bot state machine split

Reason:

Bot behavior has shown real bugs and user-facing stalls. The logic should be easier to reason about.

Target:

- `apps/api/app/modules/business_intake/service.py`

Goal:

- Extract conversation update handling from the service.
- Keep endpoints and storage unchanged.

### Cut 3: Credits approval transaction split

Reason:

Money/credit mutation must be highly readable.

Target:

- `apps/api/app/modules/credits/repository.py`
- `PostgresCreditRepository.approve_purchase`

Goal:

- Keep atomic transaction.
- Split internal helpers.
- Preserve exact behavior.

### Cut 4: Orders service split

Reason:

Core marketplace lifecycle is concentrated in long service methods.

Target:

- `apps/api/app/modules/orders/service.py`

Goal:

- Extract helper methods for create order, payment report and business confirmation.

### Cut 5: CSS split

Reason:

Not urgent, but important for long-term UI consistency.

Target:

- `apps/web/src/app/globals.css`

Goal:

- base + client + business + admin css files.

## What Not To Do

Do not rewrite everything at once.

Do not change endpoints while refactoring.

Do not change business rules while splitting files.

Do not combine UI polish with backend service cuts.

Do not touch deploy during these architecture cuts.

## Final Assessment

The architecture has improved a lot. The app surfaces are now separated and the Admin Web model is much cleaner.

But there are still real cleanup targets. The next surgical cut should be:

```txt
Split apps/web/src/screens/client/RemitterScreens.tsx into small client screen files.
```

That is the highest-signal frontend repair before continuing product polish.
