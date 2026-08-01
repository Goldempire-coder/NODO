# Builder Prompt

Actua como Builder senior de frontend para NODO. Implementa Slice 50C:
`native chat surface and keyboard rescue`.

Repo:
`C:\Users\carlo\Documents\Playground\NODO`

Rama:
`codex/intake-admin-review-v2`

Lee primero todos los contratos de este mismo directorio:

- `README.md`
- `SCOPE.md`
- `UI_CONTRACT.md`
- `SECURITY_CONTRACT.md`
- `QA.md`

Visual references:

- Current problem:
  `C:\Users\carlo\Downloads\Codex Image Aug 1, 2026, 03_02_06 PM.jpg`
- Target direction:
  `C:\Users\carlo\Downloads\ChatGPT Image Aug 1, 2026, 03_05_53 PM.png`

## Objective

Turn Cliente, Negocio and Soporte chat surfaces into native-feeling mobile chat
screens.

The current problem is not the keyboard alone. The fixed UI consumes too much
vertical space before the keyboard opens. With the keyboard open, the user
cannot comfortably see messages or what they are typing.

## Product Rules

- No fixed `Tracking y chat` header inside the chat screen.
- No permanent fixed block for `Chat con negocio`, order code or business name.
- Move order/business metadata into a derived system bubble inside the message
  list.
- Floating back control.
- No persistent refresh control; use the silent refresh and expose a compact
  recovery action only with an error.
- Compact action chips for payment actions.
- Composer fixed directly above the keyboard.
- Only the conversation scrolls.
- No page jump, zoom or delayed forced scroll on focus.
- No full-width payment bars that reserve vertical space.
- No extra forms, cards or steps.

## Implementation Guidance

Likely files:

- `apps/web/src/screens/client/ClientOrderChatScreen.tsx`
- `apps/web/src/screens/business-app/BusinessChatScreen.tsx`
- `apps/web/src/screens/client/ClientSupportScreen.tsx`
- `apps/web/src/screens/business-app/BusinessSupportScreen.tsx`
- `apps/web/src/screens/client/ClientWorkspaceShell.tsx`
- `apps/web/src/screens/business-app/BusinessMiniAppShell.tsx`
- `apps/web/src/hooks/useMobileKeyboardViewport.ts`
- `apps/web/src/app/globals.css`
- existing static tests for chat/support/mobile keyboard behavior.

Use existing DTO fields. Do not add backend endpoints unless a required public
order code/business name is unavailable.

## Security Rules

- Do not change chat authorization.
- Do not expose storage paths or signed URLs.
- Do not auto-open private attachments.
- Do not persist the derived system bubble as a message.
- Do not create Telegram notification jobs for the derived system bubble.
- Keep action buttons capability-driven.

## Required Validation

Run:

```powershell
python -m pytest apps/api/tests/test_business_order_chat_ui_static.py apps/api/tests/test_business_support_ui_static.py apps/api/tests/test_simplified_p2p_negotiation_flow_static.py apps/api/tests/test_auth_lifecycle_static.py -q --tb=short
python -m pytest apps/api/tests/test_chat_disputes.py apps/api/tests/test_payment_instructions_reports.py -q --tb=short
python -m pytest apps/api/tests -q
python -m ruff check apps/api scripts
python -m compileall apps/api apps/web/src scripts
pnpm --filter @nodo/web build
git diff --check
```

Run Secret Guard over touched files.

If browser tooling is available, capture a mobile viewport screenshot with the
keyboard-safe layout emulated as closely as possible. If real Telegram/iPhone or
Android smoke is not available, report it as a risk. Do not declare
`READY_FOR_REAL_USE`.

## Report Final

Return:

1. Estado.
2. What changed in Cliente chat.
3. What changed in Negocio chat.
4. What changed in Soporte.
5. Files touched.
6. Validation.
7. Staging/deploy status.
8. Risks pending.
9. Confirmation: no production, no secrets, no data deletion, no payment-state
   changes.
