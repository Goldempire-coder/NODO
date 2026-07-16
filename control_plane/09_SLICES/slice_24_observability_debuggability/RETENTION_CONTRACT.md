# RETENTION_CONTRACT - slice_24_observability_debuggability

## Retention defaults

- Local ring buffer: current browser session only.
- Backend persisted events in staging: 7 days by default.
- Production persistence: disabled until owner approval.
- Admin export artifacts: 24 hours unless owner approves longer retention.

## Cleanup

Job: `cleanup_observability_events`.

Rules:

- Delete only rows where `expires_at < now()`.
- Must support dry-run.
- Must log summary without private data.
- Must not delete audit logs.
- Must not delete business data.

## Cost controls

- Sampling rate configurable by `OBSERVABILITY_SAMPLE_RATE`.
- Max events per session/day: `500`.
- Max event size: `2048` bytes.
- Max batch size: `20`.
- Max retained breadcrumbs in frontend: `50`.
- Ingest interval: minimum `5` seconds between batches per session unless flushing on unload/error.
- Rate limit by user/session/IP.
