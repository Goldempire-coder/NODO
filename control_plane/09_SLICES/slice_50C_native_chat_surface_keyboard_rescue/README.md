# Slice 50C Native Chat Surface And Keyboard Rescue

Status: READY_FOR_VALIDATOR_REVIEW

This slice turns the order chat and support chat into a native-feeling mobile
conversation surface.

Owner problem:

- The current chat keeps fixed headers, order metadata and payment actions above
  the composer.
- When the Telegram keyboard opens, almost all usable space disappears.
- The user cannot comfortably see what they are writing.
- The layout feels fragile instead of native on Android and iPhone.

Owner-approved direction:

- The fixed screen must stop behaving like a page with a chat inside it.
- The chat itself becomes the primary surface.
- Order/business metadata moves into a derived system bubble inside the message
  history.
- Back becomes a compact floating control; refresh remains silent and only an
  error-recovery action may be shown.
- Payment actions become small floating chips or compact inline actions, never
  full-width blocks that reserve permanent vertical space.
- The composer remains fixed directly above the keyboard.
- Only the message list scrolls.
- Opening the keyboard must not trigger zoom, page jumps or delayed forced
  scroll.

Owner follow-up:

- Order chat does not expose dispute creation. Problems are reported from the
  normal Support section, with no direct Support entry inside order chat.
- Payment and delivery actions refresh the active conversation in place; they
  must not navigate the participant back to an order list.
- Floating navigation uses a quiet shadow.
- Visible chat/support labels use complete public wording and never synthesize
  shortened internal identifiers.

Visual references available on the Owner machine:

- Current problem photo:
  `C:\Users\carlo\Downloads\Codex Image Aug 1, 2026, 03_02_06 PM.jpg`
- Target direction:
  `C:\Users\carlo\Downloads\ChatGPT Image Aug 1, 2026, 03_05_53 PM.png`

This slice is UI-only unless the implementation discovers that an existing DTO
does not expose enough order/business metadata for the derived system bubble.
No payment, credit, dispute, Zelle, USDC/Base, support backend, reputation,
storage or scheduler rule changes are part of this slice.
