# Security Contract

This slice is a UI layout repair. It must not weaken existing authorization,
privacy or evidence rules.

## Sensitive Data

- Do not expose storage paths.
- Do not expose signed URLs except through existing explicit attachment-open
  actions.
- Do not expose full hashes, Zelle account data beyond existing visible chat
  behavior, Pago Movil details, internal user IDs or private risk signals.
- Do not move sensitive fields into telemetry or breadcrumbs.

## Messages

- The derived system bubble is generated locally/server-side from order data and
  is not a participant-authored message.
- It must not be sent through Telegram notification jobs.
- It must not be inserted into `messages`.
- It must not affect anti-evasion moderation.

## Authorization

- All payment/action buttons remain capability-driven.
- Client actions remain client-only.
- Business actions remain business-owner-only.
- Support actions remain governed by existing support permissions.
- Waiting-payment chat remains participant-only through the existing chat
  policy.

## Attachments

- Existing chat attachment opening rules remain unchanged.
- Existing payment-evidence upload and report rules remain unchanged.
- No automatic prefetch of private evidence is allowed.

## Audit

No new audit event is required for visual rendering.

Existing explicit actions, such as opening attachments or reporting payment,
must keep their current audit and idempotency behavior.
