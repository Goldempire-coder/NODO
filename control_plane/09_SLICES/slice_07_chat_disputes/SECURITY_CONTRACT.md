# SECURITY_CONTRACT.md

# SECURITY_CONTRACT.md

Security requirements:

Only order participants can read/write `waiting_payment` chat through the
general messages endpoint. Admin/support evidence access requires its explicit
authorized viewer; the general endpoint must not expose waiting-payment bodies.
Attachments are private. Slice 07 does not include admin resolution. Slice 09
admin resolution requires reason and audit. No public evidence URLs.

Mandatory controls:

- Backend RBAC, not frontend-only hiding.
- Ownership checks for user/business/order resources.
- Rate limits on sensitive or high-traffic endpoints.
- Secrets never in frontend bundle or repo.
- Audit log for sensitive state/data changes.

## Ownership

- Remitter can read/write messages only on own order.
- Business owner can read/write messages only on own business order.
- Admin/super_admin can read disputes/messages for review only.
- Support can read disputes/messages only if RBAC allows read-only support.
- Admin/super_admin/support cannot resolve disputes in slice 07.
- `resolve_dispute` belongs to `slice_09_admin_console`, not slice 07.
- Guest cannot access any chat/dispute endpoint.
- Permission errors must not reveal private order/dispute existence.

## Attachments

- Use `file_assets` and private storage.
- `file_assets.resource_type = message`.
- `file_assets.file_type = message_attachment`.
- Allowed MIME: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`.
- Max size: 5 MB.
- Signed URLs are short lived and not persisted.
- Slice 07 API responses return metadata only; no signed URL endpoint is in scope.
- `storage_path` must never appear in API, frontend, logs or audit metadata.

## Sensitive data

- Free `messages.body`, chat attachments, list and dispute responses contain no
  full Pago Movil instructions.
- Slice 50B may render a separately fetched `chat-style secure receiver
  payload` for the two participants. It is not a message body and is excluded
  from this general chat endpoint.
- No `account_value` in chat/list/dispute responses.
- No tokens, secrets, storage paths or raw private file keys in logs.
- Free text must be sanitized before display.

If any control is missing, stop with BLOCKED_BY_SECURITY_GAP.
