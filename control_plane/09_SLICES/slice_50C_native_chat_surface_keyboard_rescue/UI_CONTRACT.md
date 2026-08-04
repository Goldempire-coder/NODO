# UI Contract

## Fixed Surface

The fixed chat surface contains only:

- floating back control;
- scrollable message list;
- compact action chip rail when actions are available;
- composer fixed above the keyboard.

The fixed chat surface must not contain:

- `Tracking y chat`;
- a permanent `Chat con negocio` or `Chat con cliente` block;
- a permanent public order code block;
- a permanent business name block;
- full-width `Foto` or `Zelle enviado` rows;
- a separate `Foto` action outside the composer;
- card-style payment forms;
- page-level scroll as the primary interaction.

The chat relies on the existing silent refresh. A refresh control is rendered
only alongside an error recovery notice; it is not a persistent chat control.

Order chat must not render a dispute form, dispute action or direct entry to
Support. Participants use the normal Support section outside the order chat.
The conversation stays focused on negotiation and payment state.

## Derived System Bubble

At the top of the order-chat message list, render a derived system bubble:

```text
NODO
Negociacion abierta con {business_name}
Orden {public_order_code}
```

Rules:

- This bubble is generated from current order data.
- It is not persisted as a user message.
- It does not create Telegram notifications.
- It scrolls away like a normal message.
- It must not duplicate if the chat refreshes.
- It must not expose internal IDs when `public_order_code` exists.
- If a public code is unavailable, show a neutral complete label such as
  `Orden en curso`; never abbreviate an internal UUID.

Support chats may keep their own ticket metadata as a scrollable system bubble,
not a fixed header, if that metadata currently consumes keyboard space.

## Floating Controls

Floating controls must:

- stay outside the composer;
- avoid covering the latest message or the text being typed;
- have a safe hit target;
- use icons where possible;
- be visually quiet.

Action chips must be small:

- max one line;
- no full-width row unless desktop/tablet layout requires it;
- visible only when the backend capability allows the action;
- disabled state must be clear but compact.

Floating controls and action chips must never cover messages or the composer.
The message viewport must reserve the small safety inset needed by visible
floating actions.

The composer paperclip owns attachment selection. During the pre-payment Zelle
report flow it may select optional payment evidence; there is no second `Foto`
button and the absence of a file does not disable `Zelle enviado`.

Sensitive actions keep explicit labels:

- Client: `Zelle enviado` and `Recibi el pago`.
- Business: `Compartir datos de pago`/`Compartir wallet`, `Confirmar pago recibido` and
  `Pago Movil enviado`.

After a successful action, its chip disappears when the backend capability no
longer allows it. The resulting backend state may render as a derived system
bubble; it must not be fabricated as a free-form chat message.

Successful client and business order actions refresh the active chat and order
state in place. Background order-list synchronization must never navigate away
from the open chat.

Visible labels must use complete words. In particular, do not render shortened
internal ticket/order IDs or the abbreviated `Tx hash` label.

## Keyboard Behavior

When the keyboard opens:

- the app does not zoom;
- the root page does not jump;
- the chat does not switch to a different structural mode;
- no delayed forced scroll is triggered on focus;
- only the available message viewport height changes;
- the composer remains visible directly above the keyboard;
- the message list remains scrollable.

Telegram already supplies the `NODO` application bar. An open chat must not add
a second application header or a second fixed title inside the web surface.

When the keyboard closes:

- no manual restoration animation is required;
- floating actions and available controls remain in their normal compact
  positions.

## Typography

- All visible `input`, `textarea` and `select` controls in mini-app chat/support
  surfaces must use at least `16px`.
- Message body text should remain readable at mobile size.
- Do not reduce message text to solve keyboard crowding.

## Mobile Layout

Target minimum viewport:

- 360px wide Android Telegram WebView;
- iPhone Telegram WebView with dynamic keyboard;
- safe-area bottom inset.

The chat must remain usable with approximately half the viewport occupied by
the keyboard.
