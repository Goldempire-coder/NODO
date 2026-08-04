# QA

50B0 is documentation-only. These are required future runtime tests.

## State and Accounting

- Full happy path reaches `completed`.
- Reporting payment changes only `waiting_payment -> payment_reported`; it does
  not consume publication credit.
- Official business confirmation changes
  `payment_reported -> payment_confirmed` and consumes publication credit once.
- Business writing `recibido` in chat creates only a message and notification.
- Business cannot use simple cancellation after `payment_reported`.
- Pre-report cancel/expiration releases operational capacity once.
- `payment_reported`, `payment_rejected`, `payment_confirmed`, `delivered` and
  `disputed` retain operational capacity.
- Manual and automatic completion consume operational capacity once.

## Secure Receiver Details

- Remitter can submit structured receiver details only for own
  `payment_confirmed` order.
- The client uses a compact structured chat UI; plain message text is never
  parsed into receiver details.
- After explicit reveal, the business can copy phone, document, bank or the
  complete structured set locally.
- Business cannot mark delivered from `payment_confirmed` until structured
  receiver details exist for that same order.
- Payload replay is idempotent; changed payload with same key conflicts.
- A different key cannot replace already accepted receiver details.
- A valid replay after the order advances returns the existing resource; it
  does not fail the first-creation state guard or duplicate effects.
- Legacy create-order `receiver_data` cannot replace chat coordination and is
  removed/deprecated before real-use activation.
- Unrelated client/business gets not found.
- Admin/support cannot use the participant endpoint.
- Receiver details are absent from message rows, message API, logs, audit
  metadata, telemetry, Telegram, search, broad admin DTOs and frontend bundle.
- Error responses never echo receiver values.

## Completion and Dispute Races

- Remitter can confirm receipt only for own `delivered` order.
- Manual completion creates one event/audit/notification and no credit consume.
- Auto-complete after 24 hours uses the same atomic transition.
- Auto-complete before 24 hours is skipped.
- Open/in-review dispute blocks manual and automatic completion.
- Concurrent `delivered -> disputed` and `delivered -> completed` has exactly
  one winner and no split capacity/event/audit effects.
- Auto-complete enables rating only when the rating contract permits it.
- Manual completion enables rating only when the rating contract permits it.

## Notifications

- Receiver-details notification contains no receiver data.
- Completion notification is generic and deduplicated.
- 12-hour and 23-hour reminders are deduplicated and contain no private data.
- Telegram failure leaves the committed order state unchanged and follows the
  existing retry/permanent-failure contract.

## Contract Validation

```powershell
git diff --check
rg -n "completed.*consume.*credit|consume.*credit.*completed" control_plane
rg -n "view_order_messages|create_order_message" control_plane/05_SECURITY/RBAC_PERMISSION_MATRIX.md
rg -n "chat.*no.*full payment instructions|chat.*instrucciones completas" control_plane
```
