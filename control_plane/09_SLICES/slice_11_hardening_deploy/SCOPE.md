# SCOPE.md

## Objective

Endurecer seguridad, carga, observabilidad, backup, restore, deploy y readiness gate.

## Included

- monitoring metrics
- audit_logs
- job_runs
- backups metadata
- incident reports
- GET /health
- GET /ready
- GET /metrics internal
- admin metrics endpoints

## Affected screens

- A-12_SYSTEM_METRICS plus operational dashboards

## Explicitly excluded

- declaring READY_FOR_REAL_USE
- changing product scope
- adding features

If a requested change falls outside this scope, stop and report BLOCKED_BY_MISSING_CONTRACT or request owner approval.