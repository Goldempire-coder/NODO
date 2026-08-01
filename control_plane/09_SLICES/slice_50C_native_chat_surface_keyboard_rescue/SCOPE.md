# Scope

## Included

- Client order chat native mobile layout.
- Business order chat native mobile layout.
- Client support chat native mobile layout.
- Business support chat native mobile layout.
- Derived system bubble at the top of order chat history with:
  - NODO;
  - business name or counterparty label;
  - public order code.
- No fixed internal header for order code/business name in the chat viewport.
- Floating back control.
- No persistent refresh control; allow a compact recovery action only when an
  error is visible.
- Compact floating payment action chips:
  - `Foto`;
  - `Zelle enviado`;
  - `Zelle recibido`;
  - `Recibi el pago`;
  - equivalent support actions only where already authorized.
- Composer fixed above the keyboard with:
  - clip button;
  - 16px text input;
  - compact send icon/text button.
- Stable keyboard behavior on iPhone and Android Telegram WebView.
- Regression tests proving no `--typing` layout mode, no delayed focus scroll,
  and no full-height payment/action bars in the chat viewport.
- Documentation and QA evidence.

## Excluded

- Payment state-machine changes.
- New payment endpoints.
- Zelle contract changes.
- Credit consumption changes.
- Base USDC changes.
- Support backend rewrite.
- New attachment storage or signed URL behavior.
- Admin dashboard changes.
- Reopening, cancellation or dispute policy changes.
- Scheduler/expiration changes.
- Production deployment.
- Data cleanup.

## Non-goals

- Do not recreate WhatsApp visually one-to-one.
- Do not add decorative UI, marketing copy, cards or tutorials.
- Do not make the chat less scannable to satisfy a mockup.
- Do not hide critical irreversible actions without an available alternative.
