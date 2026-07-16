# BUILDER_PROMPT - slice_24_observability_debuggability

MODO: BUILD_ONLY_AFTER_CONTRACT_APPROVAL

Construye observabilidad segura para NODO segun estos contratos:

- `DATA_CONTRACT.md`
- `API_CONTRACT.md`
- `STATE_CONTRACT.md`
- `SECURITY_CONTRACT.md`
- `PRIVACY_CONTRACT.md`
- `RETENTION_CONTRACT.md`
- `UI_CONTRACT.md`
- `QA.md`

Scope:

- request logging estructurado backend;
- correlation/request/operation/session ids;
- redaction helper;
- frontend breadcrumbs seguros;
- session replay estructurado sin video;
- ingestion backend env-gated;
- Admin Web diagnostic search/export redacted;
- cleanup TTL;
- tests/scans/evidence.

Prohibido:

- SaaS externo;
- video replay;
- secretos/tokens/initData/storage_path/account_value/signed URLs;
- mensajes completos;
- documentos completos;
- cambiar reglas de negocio;
- deploy;
- `READY_FOR_REAL_USE`.

Validacion minima:

- pytest completo;
- ruff;
- compileall;
- frontend build;
- scans de secretos/datos privados;
- tests de redaccion, rate limit, RBAC, disabled-by-config y retention cleanup.

Estado final esperado: `READY_FOR_OWNER_REVIEW`.
