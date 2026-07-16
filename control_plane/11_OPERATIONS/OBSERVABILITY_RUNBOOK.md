# OBSERVABILITY_RUNBOOK

## Purpose

Operational guidance for slice 24 observability after build approval.

## Search keys

Operators may search diagnostic evidence by:

- `request_id`
- `correlation_id`
- `operation_id`
- `session_id`
- `business_id`
- `order_id`
- `ticket_id`
- `credit_purchase_id`
- `telegram_update_id`
- date/time
- app version/build id

## Privacy rules

Never paste secrets, tokens, signed URLs, `storage_path`, `account_value`, complete messages, documents or full tx hashes into incident notes.

## Incident reconstruction

Minimum reconstruction:

1. Identify request/correlation/session id.
2. Check backend request log by route template/status/duration/error code.
3. Check redacted frontend breadcrumb timeline if enabled.
4. Check audit log for sensitive state changes.
5. Check domain resource state from authoritative backend data.
6. Export only redacted diagnostic evidence when required.

## Production posture

Persistent frontend observability remains disabled in production until owner approval.
