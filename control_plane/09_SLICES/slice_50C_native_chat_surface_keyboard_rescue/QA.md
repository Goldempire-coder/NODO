# QA

## Required Regression Coverage

- Client order chat has no fixed `Tracking y chat` header.
- Business order chat has no fixed `Tracking y chat` header.
- Order code and business/counterparty name render as a derived system bubble
  inside the message list.
- The derived system bubble is not sent as a persisted message.
- The derived system bubble does not duplicate after refresh.
- Back control is compact/floating.
- There is no persistent refresh control; recovery is shown only with an error.
- `Foto`, `Zelle enviado`, `Zelle recibido` and completion actions are compact
  chips/actions, not permanent full-width vertical bars.
- Optional payment evidence is selected from the composer paperclip, not a
  separate `Foto` button, and its absence does not block `Zelle enviado`.
- Floating controls never cover the latest message or composer.
- Successful financial actions disappear based on refreshed backend
  capabilities and may render only as derived state bubbles.
- Action labels match role ownership: the business never sees an ambiguous
  `Enviar Zelle` action.
- The composer includes clip, input and send in one stable row.
- The composer uses at least `16px` text.
- Support composer uses at least `16px` text.
- No `business-order-chat--typing` or `business-support--typing` layout mode
  exists.
- No focus handler triggers delayed forced scroll such as
  `window.setTimeout(...scroll...)`.
- The chat message list has `overflow-y: auto`,
  `-webkit-overflow-scrolling: touch`, `touch-action: pan-y` and
  `overscroll-behavior: contain`.
- Global attention banners and success toasts do not cover the open chat.
- Empty/terminal chats remain readable and do not hide the composer when sending
  is allowed.
- Existing attachment opening tests still pass.
- Existing Zelle report tests still pass.
- Order chat contains no dispute selector or dispute-submit action.
- Client and business order chat contain no direct Support action or route.
- Problems are opened from the normal Support section outside the order chat.
- Reporting payment does not call a navigation-producing order-list loader.
- Reporting payment does not navigate to `report-payment` or launch a bank or
  wallet application.
- Business confirmation/delivery applies the returned order in place before a
  full conversation refresh.
- Chat and support never derive visible identifiers by truncating internal
  UUIDs.
- The transaction identifier label is written in full.
- The floating back control uses a quiet shadow.
- Completed and cancelled client orders do not expose a reopen-chat action in
  the client order list.

## Manual Smoke

Run in Telegram Mini App:

1. Android client chat:
   - open order chat;
   - focus composer;
   - type a long message;
   - confirm no zoom, jump or hidden input;
   - confirm last messages remain visible/scrollable.
2. Android business chat:
   - repeat the same checks.
3. iPhone client chat:
   - repeat the same checks.
4. iPhone business chat:
   - repeat the same checks.
5. Client support and business support:
   - focus composer;
   - type;
   - attach file if available;
   - confirm composer remains visible.
6. Zelle flow:
   - business shares Zelle;
   - client taps `Zelle enviado` without attaching proof;
   - confirm the report succeeds and stays in chat;
   - repeat with optional proof and confirm it remains linked to the order;
   - confirm `Zelle enviado` disappears after backend confirmation;
   - confirm the resulting state appears without a fabricated user message.

## Commands

```powershell
python -m pytest apps/api/tests/test_business_order_chat_ui_static.py apps/api/tests/test_business_support_ui_static.py apps/api/tests/test_simplified_p2p_negotiation_flow_static.py apps/api/tests/test_auth_lifecycle_static.py -q --tb=short
python -m pytest apps/api/tests/test_chat_disputes.py apps/api/tests/test_payment_instructions_reports.py -q --tb=short
python -m pytest apps/api/tests -q
python -m ruff check apps/api scripts
python -m compileall apps/api apps/web/src scripts
pnpm --filter @nodo/web build
git diff --check
```

Also run Secret Guard over touched files.

Current client UI regressions are source-level pytest checks. Async A-to-B race
behavior in a real React/browser harness remains `NOT_TESTED` until a dedicated
frontend test runner is approved and installed; static checks must not be
reported as proof of browser concurrency behavior.

## Staging Gate

Do not declare `READY_FOR_REAL_USE` until the mobile smoke passes in Telegram on
both iPhone and Android.
