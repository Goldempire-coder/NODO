# ERROR_CASES - slice_24_observability_debuggability

- `OBSERVABILITY_DISABLED`: ingestion or query disabled by config.
- `OBSERVABILITY_EVENT_INVALID`: event shape, type or metadata invalid.
- `OBSERVABILITY_EVENT_TOO_LARGE`: one event exceeds max size.
- `OBSERVABILITY_BATCH_TOO_LARGE`: batch exceeds event count or byte limit.
- `OBSERVABILITY_RATE_LIMITED`: session/user/IP exceeded ingest limit.
- `OBSERVABILITY_ACCESS_DENIED`: admin/support/staff lacks permission.
- `OBSERVABILITY_RETENTION_INVALID`: invalid retention or cleanup request.
- `OBSERVABILITY_EXPORT_BLOCKED`: export exceeds allowed window, scope or role.

Error responses must include `request_id` and safe `error.code`.

Error responses must not include stack traces, SQL, raw payloads, tokens, signed URLs, `storage_path`, `account_value` or full tx hashes.
