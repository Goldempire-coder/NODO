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
4. `GET /api/v1/orders/{id}/messages` returns derived `system_messages` and
   payment-sharing capabilities.
5. `POST /api/v1/orders/{id}/share-zelle` inserts the configured Zelle once.
6. Zelle payment instructions and reporting fail with
   `ORDER_PAYMENT_DETAILS_NOT_SHARED` until the configured account appears in a
   visible business-owner message.
7. The initial chat page is the latest bounded window, ordered oldest-to-newest
   within that window. Its cursor loads older messages.

No quote endpoint was added. The confirmation screen is read-only and has no
backend side effects. The existing order endpoint remains the authoritative
final validation and verifies the rate that the client confirmed.

Client UI behavior:

- `order-chat` refreshes `GET /messages` only while the view and document are
  visible. Refreshes do not overlap and a silent failure preserves current
  messages and capabilities.
- `Pago enviado` calls `GET /payment-instructions` in the background to preserve
  the existing reveal/audit contract, then opens `report-payment` directly.
- Failure to load instructions leaves the client in the chat.
- A late instructions response is discarded if the client changed chat or
  started opening another order.
- The removed `payment-instructions` client view is not part of the flow.
