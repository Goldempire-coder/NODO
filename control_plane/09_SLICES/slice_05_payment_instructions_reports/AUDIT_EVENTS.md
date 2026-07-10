# AUDIT_EVENTS.md

Required audit events:

- payment_instructions_viewed
- payment_evidence_uploaded
- payment_reported

Canonical reveal audit event:

```txt
payment_instructions_viewed
```

`payment_data_revealed` may be used only as UI/state wording if needed. It is not the canonical audit event for this slice.

Audit rules:

- Include actor_user_id, actor_role, resource_type, resource_id, old/new state where applicable, reason, request_id/job_id and timestamp.
- Include idempotency key metadata for retryable mutating endpoints when available.
- Audit logs are append-only.
- Do not write full payment instructions, full account values, full tx hashes where avoidable, storage paths, signed URLs, tokens or secrets into audit metadata.
