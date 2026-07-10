# DATA_CONTRACT.md

Authoritative data touched by this slice:

- monitoring metrics
- audit_logs
- job_runs
- backups metadata
- incident reports

Rules:

- Use migrations, not manual DB edits.
- Add constraints and indexes for every hot query.
- Never store money/tasa values as float.
- Sensitive fields must be masked in admin/UI where full value is not required.
- Every state-changing record must be traceable through audit_logs or state events.

Builder must update 04_DATA/DATA_MODEL_MASTER.md, DATABASE_CONSTRAINTS.md and INDEXES.md if implementation needs fields not listed here.