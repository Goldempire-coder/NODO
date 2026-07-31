# Security Contract

- Order creation, capacity reservation, ad locking and cancellation retain the
  transaction and idempotency guarantees from Slice 49A.
- Chat access is ownership checked and returns 404 to unrelated users.
- A client message containing the configured Zelle does not unlock payment.
- Account matching is case-insensitive but requires a complete literal token;
  a different address containing the configured value as a substring does not
  unlock payment.
- Authorized configured Zelle is exempt only from contact-value moderation.
  Platform-bypass language and other external contacts remain detectable.
- Full Zelle is limited to the private participant message and payment
  instruction response after sharing.
- Full Zelle is forbidden from logs, audit metadata, Telegram metadata,
  breadcrumbs and admin notification metadata.
- The virtual system message is not persisted and creates no notification.
- Payment amount remains backend validated and is read-only in the client UI.
- Opening a payment report resets prior reference, sender and evidence state so
  data from one order cannot appear in another order's form.
