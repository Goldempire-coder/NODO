# RUNBOOK: API returns 5xx

Estado de validacion: NOT VALIDATED

## 1. SINTOMA

Usuarios ven errores, Admin Web falla, o `/api/v1/*` devuelve 500.

## 2. SEVERIDAD INICIAL

SEV-1 si afecta auth, ordenes, creditos o admin. SEV-2 si es parcial.

## 3. IMPACTO

Puede bloquear cliente, negocio, soporte o admin.

## 4. PRIMEROS CINCO MINUTOS

1. Ejecutar:
   ```powershell
   Invoke-RestMethod "$env:NODO_STAGING_API_BASE_URL/health" -Headers @{"X-Request-Id"="rb_5xx_health_<timestamp>"}
   Invoke-RestMethod "$env:NODO_STAGING_API_BASE_URL/ready" -Headers @{"X-Request-Id"="rb_5xx_ready_<timestamp>"}
   Invoke-RestMethod "$env:NODO_STAGING_API_BASE_URL/version" -Headers @{"X-Request-Id"="rb_5xx_version_<timestamp>"}
   ```
2. Revisar ultimo deploy.
3. Preservar request IDs.

## 5. DIAGNOSTICO

- Si `/ready` falla, revisar DB/Redis.
- Si `/health` pasa y `/ready` pasa, revisar endpoint especifico y logs.
- Buscar `ApiError`, `OperationalError`, `DB_POOL_SATURATED`, stack traces.

## 6. ARBOL DE DECISION

- Si `/ready` 503: abrir DB/Redis runbook.
- Si solo un endpoint falla: congelar cambios en ese flujo.
- Si empezo tras deploy: considerar rollback.

## 7. MITIGACION

- Pausar flujo afectado desde UI solo si existe control documentado.
- Rollback si deploy reciente y no hubo migracion incompatible.

## 8. RECUPERACION

Aplicar fix o rollback, luego validar.

## 9. VALIDACION

- Health/ready/version OK.
- Flujo afectado OK.
- 5xx cesa.

## 10. ROLLBACK

Ver `operations/sops/ROLLBACK_SOP.md`.

## 11. ESCALAMIENTO

SEV-1: owner tecnico/operativo inmediatamente.

## 12. EVIDENCIA

Request IDs, endpoint, version, logs redacted.

## 13. PROHIBICIONES

No editar DB para ocultar el error.
