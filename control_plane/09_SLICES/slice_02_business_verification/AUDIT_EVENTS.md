# AUDIT_EVENTS.md

Required audit events:

- business_created
- business_updated
- business_submitted
- business_approved
- business_rejected
- payment_method_added
- verification_document_uploaded
- verification_document_viewed

Audit rules:

- Include `actor_user_id`, `actor_role`, `resource_type`, `resource_id`, old/new state where applicable, `reason`, `request_id`, optional `job_id` and timestamp.
- Admin sensitive actions require reason.
- Audit logs are append-only.
- Use `resource_type/resource_id`, not `entity_type/entity_id`.
- Do not store raw documents, storage paths, signed URLs, tokens, secrets or full payment account values.

Resource mapping:

- `business_created`: `resource_type = business`, `resource_id = businesses.id`.
- `business_updated`: `resource_type = business`, `resource_id = businesses.id`.
- `business_submitted`: `resource_type = business_verification_submission`, `resource_id = submission.id`.
- `business_approved`: `resource_type = business`, `resource_id = businesses.id`.
- `business_rejected`: `resource_type = business`, `resource_id = businesses.id`.
- `payment_method_added`: `resource_type = business_payment_method`, `resource_id = method.id`.
- `verification_document_uploaded`: `resource_type = file_asset`, `resource_id = file_assets.id`.
- `verification_document_viewed`: `resource_type = file_asset`, `resource_id = file_assets.id`.
