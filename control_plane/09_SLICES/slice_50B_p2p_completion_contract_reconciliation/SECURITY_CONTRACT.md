# Security Contract

## Secure Receiver Payload

Pago Movil receiver details are a high-sensitivity order resource.

- They are not `messages.body`, attachments, audit metadata or notification
  metadata.
- The UI may render a `chat-style secure receiver payload` only after an
  authorized API response.
- Only the remitter and business owner participants can use the participant
  create/read endpoints.
- Ownership and state are revalidated on every request.
- Full values use `Cache-Control: private, no-store`.
- Values must not enter logs, traces, telemetry, breadcrumbs, search indexes,
  broad admin views, frontend bundles, Telegram or free-form metadata.
- Error details contain field names and safe codes only, never submitted values.
- General chat and dispute endpoints do not return this resource.
- Admin/support have no implicit access. A future explicit reveal must require
  permission, reason, purpose-bound endpoint and audit.
- Creating or revealing full receiver details fails closed if its required safe
  audit record cannot be persisted. A successful sensitive write/reveal may not
  exist without its corresponding audit.

## Audit Allowlist

Allowed audit metadata:

- `order_id`;
- actor ID and role;
- receiver field-presence booleans;
- normalized schema version;
- action result;
- `request_id`, `correlation_id`, `operation_id`;
- timestamps;
- whether a dispute guard blocked completion.

Forbidden audit/log/telemetry metadata:

- bank, phone, document or holder values;
- chat bodies;
- proof bodies or file paths;
- `account_value`, `storage_path`, signed URLs;
- tokens, PINs, authorization headers or secrets.

## Completion Safety

- Deep links and UI visibility are not authorization.
- Manual and automatic completion share one backend-authoritative transaction.
- The transaction must prevent `delivered -> completed` from racing past an
  `open|in_review` dispute.
- Publication credit and operational capacity use separate exact-once ledgers
  or equivalent uniqueness guarantees.
- Notification failure after commit never rolls back a completed order.

## Masking

Masked summaries may show only the minimum needed to identify a previously
shared receiver. They must not permit reconstruction of the full phone,
document or holder.
