# RUNBOOK: Defective deployment

Estado de validacion: NOT VALIDATED

## SINTOMA

Problemas comienzan justo despues de deploy.

## SEVERIDAD INICIAL

SEV-1/2 segun impacto.

## PRIMEROS CINCO MINUTOS

1. Confirmar version:
   ```powershell
   Invoke-RestMethod "$env:NODO_STAGING_API_BASE_URL/version" -Headers @{"X-Request-Id"="rb_deploy_version_<timestamp>"}
   ```
2. Revisar si hubo migracion.
3. Congelar nuevos deploys.

## MITIGACION

- Rollback provider si no hay migracion incompatible.
- Si hubo migracion, escalar antes de rollback.
- Si el codigo y schema quedaron incompatibles, usar `SCHEMA_DEPLOY_INCOMPATIBILITY_RUNBOOK.md`.
- Rollback debe seguir `operations/sops/ROLLBACK_SOP.md`.

## PROHIBICIONES

- No hacer deploy encima sin causa.
- No ejecutar down migration improvisada.
- No declarar recuperacion sin `/health`, `/ready`, `/version` y smoke del flujo afectado.
