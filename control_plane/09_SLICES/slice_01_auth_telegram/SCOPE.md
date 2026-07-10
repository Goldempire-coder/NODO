# SCOPE.md

## Objective

Autenticar usuarios desde Telegram Mini App y emitir sesion backend segura.

## Included

- users
- sessions
- audit_logs
- POST /api/v1/auth/telegram
- POST /api/v1/auth/refresh
- POST /api/v1/auth/logout
- GET /api/v1/users/me

## Affected screens

- R-01_WELCOME_ENTRY
- profile session states

## Explicitly excluded

- business verification
- marketplace
- orders
- admin approvals

If a requested change falls outside this scope, stop and report BLOCKED_BY_MISSING_CONTRACT or request owner approval.
