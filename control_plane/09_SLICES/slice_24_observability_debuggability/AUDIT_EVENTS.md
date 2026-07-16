# AUDIT_EVENTS - slice_24_observability_debuggability

Observability ingestion itself is operational and should not create one audit event per breadcrumb.

Audit is required for:

- `observability_events_viewed`
- `observability_session_viewed`
- `observability_export_created`
- `observability_retention_cleanup_run`
- `observability_access_denied`
- `observability_config_changed`

Audit metadata must contain only:

- actor id;
- role/staff permission summary;
- filter summary;
- reason when required;
- request_id/correlation_id;
- counts;
- redaction status.

Audit metadata must not contain raw observability event payloads, tokens, signed URLs, storage paths, account values, message bodies or full tx hashes.
