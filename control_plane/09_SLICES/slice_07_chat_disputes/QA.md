# QA.md

Required QA:

- party isolation
- open dispute reasons
- auto-complete blocked by dispute
- admin resolution not built in slice 07
- attachments signed/private
- messages use `messages`, not `chat_messages`
- R-10 confirm received is not built
- message audit uses `message_created`
- dispute messages use `dispute_message_created`
- attachments audit uses `message_attachment_uploaded`
- message attachment upload rejects invalid MIME
- message attachment upload rejects file > 5 MB
- attachment responses never expose `storage_path`
- opening dispute sets `orders.status = disputed`
- opening dispute stores `previous_order_status`
- dispute from `payment_reported/payment_rejected` keeps credits blocked and ad `in_order`
- dispute from `payment_confirmed/delivered` keeps credits consumed and ad `archived`
- no admin resolve endpoint is built
- no completion/rating/auto-complete is built

Gate:

- Unit tests for services/state/policies.
- Integration tests for endpoints.
- RBAC/ownership tests.
- Audit event verification.
- Manual smoke for affected screens.
- Builder report must list commands run and tests not run with reason.
