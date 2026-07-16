# SOP: Rollback

SOP_ID: SOP-ROLLBACK-001
Estado de validacion: NOT VALIDATED
Ultima fecha de validacion: 2026-07-11

## Proposito

Revertir un deploy defectuoso sin empeorar datos o seguridad.

Rollback de codigo no es backup/restore. Si hay perdida, corrupcion o inconsistencia de datos, este SOP no autoriza restore; usar `RESTORE_SOP.md` y el runbook de DR correspondiente.

## Alcance

Railway backend, Cloudflare Pages frontend y migraciones DB.

## Tier afectado

Tier 0/1.

## Cuando utilizarlo

- Deploy causa 5xx, latencia severa o errores de flujo principal.
- Frontend apunta al API incorrecto.
- Admin/negocio/cliente no pueden operar.

## Cuando no utilizarlo

- Si el incidente es por datos corruptos o migracion irreversible sin plan.
- Si rollback ejecutaria codigo viejo incompatible con schema actual.
- Si el provider rollback requiere comandos no documentados.

## Procedimiento

1. Confirmar build/version actual:
   ```powershell
   Invoke-RestMethod "$env:NODO_STAGING_API_BASE_URL/version" -Headers @{"X-Request-Id"="rollback_version_<timestamp>"}
   ```

2. Revisar si hubo migracion DB en el deploy.
   - Si si, detener rollback automatico y escalar.
   - Revisar `runbooks/SCHEMA_DEPLOY_INCOMPATIBILITY_RUNBOOK.md`.
   - Si no, continuar con rollback del proveedor.

3. Ejecutar rollback en Railway/Cloudflare.
   - Comando exacto: COMMAND NOT AVAILABLE.
   - Decision requerida: owner debe aprobar el mecanismo exacto de Railway/Cloudflare antes de produccion.

4. Validar:
   ```powershell
   Invoke-RestMethod "$env:NODO_STAGING_API_BASE_URL/health" -Headers @{"X-Request-Id"="rollback_health_<timestamp>"}
   Invoke-RestMethod "$env:NODO_STAGING_API_BASE_URL/ready" -Headers @{"X-Request-Id"="rollback_ready_<timestamp>"}
   Invoke-RestMethod "$env:NODO_STAGING_API_BASE_URL/version" -Headers @{"X-Request-Id"="rollback_version_after_<timestamp>"}
   ```

## Criterio de exito

- Version esperada activa.
- `/ready` pasa.
- Flujo afectado recuperado.

## Criterio de aborto

- Rollback requiere DB downgrade no probado.
- Provider rollback falla.
- Sigue habiendo SEV-1.

## Evidencia

- Version antes/despues.
- Hora del rollback.
- Request IDs.

## Estado

BLOCKED para produccion hasta documentar comandos provider exactos.
