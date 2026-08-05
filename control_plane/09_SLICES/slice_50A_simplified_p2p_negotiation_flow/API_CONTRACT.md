# API Contract

Canonical contracts:

- `control_plane/06_API_CONTRACTS/ORDERS_API.md`
- `control_plane/06_API_CONTRACTS/MESSAGES_API.md`
- `control_plane/06_API_CONTRACTS/ERROR_CONTRACT.md`

Slice additions:

1. `POST /api/v1/orders` accepts omitted `receiver_data`.
2. `POST /api/v1/orders` accepts optional `expected_rate_bs_per_usd` and
   rejects a stale confirmation with `409 ORDER_QUOTE_CHANGED`.
3. `GET/POST /api/v1/orders/{id}/messages` accepts `waiting_payment` for the
   order participants.
4. `GET /api/v1/orders/{id}/messages` returns the current allowlisted `order`,
   derived `system_messages` and payment-sharing capabilities.
5. `POST /api/v1/orders/{id}/share-payment-details` inserts the configured
   Zelle or USDT wallet once. `share-zelle` remains a legacy Zelle alias.
6. Zelle and USDT payment instructions and reporting fail with
   `ORDER_PAYMENT_DETAILS_NOT_SHARED` until the configured account appears in a
   visible business-owner message.
7. The initial chat page is the latest bounded window, ordered oldest-to-newest
   within that window. Its cursor loads older messages.
8. `POST /api/v1/orders/{id}/message-attachments/{attachment_id}/view-url`
   opens a temporary URL only for the two order participants. It returns
   `Cache-Control: private, no-store` and never returns storage paths or
   permanent URLs.
9. `POST /api/v1/orders/{id}/payment-report` requires the locked order
   amount. Uploaded proof is optional; if supplied, its order binding and
   single-use integrity rules still apply. Legacy sender name, reference and
   account fields remain optional compatibility inputs and must never be
   fabricated.

No quote endpoint was added. The confirmation screen is read-only and has no
backend side effects. The existing order endpoint remains the authoritative
final validation and verifies the rate that the client confirmed.

Client UI behavior:

- `order-chat` refreshes `GET /messages` only while the view and document are
  visible. Refreshes do not overlap and a silent failure preserves current
  order, messages and capabilities.
- `Pago enviado` calls `GET /payment-instructions` in the background to preserve
  the existing reveal/audit contract, then submits from the active order chat.
- `report-payment` is a compatibility view, not the primary client flow. The
  normal flow does not navigate to it.
- NODO does not launch a bank or wallet application. Copying the configured
  value is a local chat action; leaving Telegram and returning is controlled by
  the client and must not discard the active order context.
- Failure to load instructions leaves the client in the chat.
- A late instructions response is discarded if the client changed chat or
  started opening another order.
- The removed `payment-instructions` client view is not part of the flow.
- Success toasts and attention banners are suppressed while the participant is
  already inside the order chat.
- Image/PDF chat attachments render as compact open actions inside the chat.
- Completed and cancelled chats are not required to reopen from the client
  order list. This does not change the backend participant-history contract.
