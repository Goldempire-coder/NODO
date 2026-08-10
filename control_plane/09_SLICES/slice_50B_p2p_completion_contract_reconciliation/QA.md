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
- Business cannot create a new `payment_rejected` transition after
  `payment_reported`; `Reportar problema con pago` atomically opens a dispute
  with reason `payment_not_received_or_incomplete`.
- Historical `payment_rejected` orders remain readable and can be escalated to
  dispute without deleting their timeline.
- Pre-report cancel/expiration releases operational capacity once.
- `payment_reported`, `payment_rejected`, `payment_confirmed`, `delivered` and
  `disputed` retain operational capacity.
- Manual and automatic completion consume operational capacity once.
- Terminal `completed|cancelled` after `paid_reported_at` extends the business
  publication pause to at least `database_now + 15 minutes` without changing
  the terminal credit, capacity or ad effect.
- Cancellation before payment reporting does not create the cooldown; an Admin
  block or restriction still wins after the cooldown expires.

## Secure Receiver Details

- Remitter can submit structured receiver details only for own
  `payment_confirmed` order.
- The client uses a compact structured chat UI; plain message text is never
  parsed into receiver details.
- After explicit reveal, the business can copy phone, document, bank or the
  complete structured set locally.
- Documents with 6..10 digits are accepted without requiring or inventing `V`.
- Optional `V|E|J|G|P` prefixes remain accepted, normalize to uppercase and
  preserve their meaning; numeric documents mask as `***NNN`.
- Local Venezuelan phone and equivalent `+58` formats remain accepted without
  changing their persisted presentation.
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
