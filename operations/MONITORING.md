# MONITORING

Estado: OFFICIAL
Ultima actualizacion: 2026-07-11

## Observabilidad existente en codigo

- Health: `GET /health` y `GET /api/v1/health`.
- Readiness: `GET /ready` y `GET /api/v1/ready`; valida Postgres y Redis.
- Version: `GET /version` y `GET /api/v1/version`.
- Response timing: headers `X-NODO-Process-Time-Ms` y `Server-Timing`.
- Logging Python con redaccion de secretos en `apps/api/app/core/logging.py`.
- Audit logs para acciones criticas.
- `job_runs` y admin endpoints de jobs.
- Evidence JSON para staging tooling y stress scripts.
- Profiling staging para marketplace bajo gate.

## Gaps bloqueantes

- No hay dashboard operacional versionado en repo.
- No hay alertas provider-as-code.
- No hay metricas agregadas de 5xx/p95/p99 en repo.
- No hay tracing distribuido.
- No hay runbook validado para revisar logs Railway por request ID.
- No hay backup/restore probado.
- No hay monitor documentado para Base USDC watcher.
- No hay alerta documentada para doble credito o `ONCHAIN_TX_ALREADY_USED`.
- No hay alerta para `DB_POOL_SATURATED` aunque los stress scans lo buscan.

## Instrumentacion minima requerida antes de produccion

- Alertas por 5xx sostenido.
- Alertas por `/ready` 503.
- Alertas por p95 API sostenido.
- Alertas por conexiones DB cerca del limite.
- Alertas por errores Redis/idempotency.
- Alertas por watcher Base USDC con errores.
- Alertas por creditos duplicados o tx hash reutilizado.
- Alertas por `USER_BLOCKED`, `BUSINESS_ACCESS_BLOCKED` anomalo si sube de golpe.
- Dashboard con deploy version/build id.
- Log query por `X-Request-Id`.
