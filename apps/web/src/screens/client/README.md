# Client App architecture

The Client App is chat-first. Screens render state and call model actions; the
backend remains authoritative for ownership, capabilities, order state, payment
rules, idempotency, and sensitive-data disclosure.

## Order chat responsibilities

- `useClientChatDisputesModel.ts` owns active-order identity, thread hydration,
  stale response rejection, Pago Movil coordination, and completion refresh.
- `useClientChatComposerModel.ts` owns drafts, uploads, sends, and temporary
  attachment links. Drafts and pending actions are keyed by `order_id`.
- `useClientOrderChatSync.ts` owns visible-only polling and payment-instruction
  loading for the active chat.
- `ClientOrderChatScreen.tsx` composes the chat surface without calling APIs.
- `screens/client/chat/` contains focused presentation components for messages,
  payment instructions, Pago Movil, and rating.

## Invariants

- A response for order A must never update visible state for order B.
- Frontend capability checks are UX guards only; the backend decides whether an
  action is allowed.
- Reporting Zelle or USDT stays in the active chat. NODO does not open a bank or
  wallet application.
- Payment evidence and message attachments remain tied to their active order.
- Completed and cancelled chats do not need to reopen from the client order
  list; the public order number remains available for support.

## Deferred cleanup

Client and Business chat currently share `business-order-chat-*` CSS classes in
`app/globals.css`. Splitting or renaming them requires a separate shared-surface
change with visual regression coverage for both apps.
