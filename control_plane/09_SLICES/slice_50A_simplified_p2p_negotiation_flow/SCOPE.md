# Scope

## Included

- Minimal client confirmation before `POST /api/v1/orders`.
- No mutation when the client returns from that confirmation.
- Backward-compatible optional `receiver_data`.
- Immediate participant chat for `waiting_payment`.
- Derived system message with no database row or Telegram job.
- Manual and compact configured-Zelle sharing.
- Literal configured-account matching.
- Backend payment gate and read-only client payment amount.
- Visible-only, non-overlapping client chat refresh scoped to `order-chat`.
- Direct transition from the chat payment action to the compact report form.
- Optional Zelle proof; absence of a photo does not block `Pago enviado`.
- Honest business-order copy when legacy `receiver_data` is absent.
- Contracts and regression tests.

## Excluded

- Credit-consumption changes.
- New final confirmation state.
- Real expiration scheduler activation.
- Public reputation penalties.
- Admin repair queue.
- General support changes.
- Base USDC changes.
- Deployment or production work.
