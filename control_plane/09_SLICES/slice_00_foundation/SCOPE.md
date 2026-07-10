# SCOPE.md

## Objective

Crear base tecnica profesional: repo, tooling, envs, CI, migraciones base, health checks, logging y estructura modular.

## Included

- users base
- audit_logs base
- job_runs base
- migrations table
- health metadata
- GET /health
- GET /ready
- GET /version

## Affected screens

- none

## Explicitly excluded

- business onboarding
- marketplace
- orders
- payments
- credits
- admin workflows

If a requested change falls outside this scope, stop and report BLOCKED_BY_MISSING_CONTRACT or request owner approval.