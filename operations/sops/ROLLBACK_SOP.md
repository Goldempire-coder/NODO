# SOP: Rollback

SOP_ID: SOP-ROLLBACK-001
Estado de validacion: NOT VALIDATED
Ultima revision documental: 2026-09-09
Ultima prueba de rollback staging: PENDING EVIDENCE

## Proposito

Revertir un deploy defectuoso sin empeorar datos o seguridad.

Rollback de codigo no es backup/restore. Si hay perdida, corrupcion o inconsistencia de datos, este SOP no autoriza restore; usar `RESTORE_SOP.md` y el runbook de DR correspondiente.

## Alcance

Railway backend y Cloudflare Pages frontend. DB se revisa por compatibilidad; este procedimiento no ejecuta migraciones, downgrade ni restore.

Este SOP cubre rollback minimo por redeploy de un SHA anterior conocido. Rollback provider nativo por UI/API Railway/Cloudflare sigue `NOT VALIDATED`.

Los comandos siguientes son una referencia para una ejecucion aprobada. La aprobacion de documentacion no autoriza desplegar ni modificar proveedores.

El nombre Railway `production` corresponde al target historico usado como staging; verificar proyecto, servicio, dominio y `environment=staging` antes de usarlo. No inferir el ambiente por el nombre del proveedor.

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

1. Confirmar target aprobado y registrar SHA actual de backend y web:
   ```powershell
   $rollbackApiUrl = "https://nodo-api-production.up.railway.app"
   $rollbackWebUrl = "https://nodo-staging.pages.dev"
   Invoke-RestMethod "$rollbackApiUrl/api/v1/version" -Headers @{"X-Request-Id"="rollback_version_<timestamp>"} -TimeoutSec 15
   Invoke-RestMethod "$rollbackWebUrl/version.json?rollback=<timestamp>" -Headers @{"Cache-Control"="no-cache"} -TimeoutSec 15
   ```
   Conservar el SHA inicial como destino de regreso. No usar HEAD como sustituto de la version efectivamente desplegada.

2. Revisar si hubo migracion DB en el deploy.
   - Si si, detener rollback automatico y escalar.
   - Revisar `runbooks/SCHEMA_DEPLOY_INCOMPATIBILITY_RUNBOOK.md`.
   - Si no, revisar tambien contratos API, configuracion, jobs, watcher y cambios de seguridad entre ambos SHA antes de continuar.

3. Si no hubo migracion incompatible, preparar un worktree limpio del SHA anterior:
   ```powershell
   $rollbackSourcePath = "C:\Users\carlo\Documents\Playground\NODO-rollback-<short_sha>"
   git worktree add --detach "$rollbackSourcePath" <previous_full_sha>
   Set-Location -LiteralPath $rollbackSourcePath
   git rev-parse --show-toplevel HEAD
   git status --porcelain=v1
   ```
   Sustituir los marcadores por datos aprobados. La ruta debe ser nueva y estar dentro del workspace previsto. HEAD debe coincidir con el SHA destino y el estado debe estar limpio; si falla un comando, detenerse.

4. Backend-first: redeploy del SHA anterior con identidad explicita:
   ```powershell
   railway up --ci --service nodo-api --environment production --project cf196334-9990-440e-8eb3-c519e4fcdf37 --message "rollback <short_sha>"
   ```
   Ejecutar desde el worktree verificado. Antes del deploy debe estar resuelto como el runtime recibira el SHA correcto: `NODO_RELEASE_COMMIT_SHA` tiene precedencia sobre `RAILWAY_GIT_COMMIT_SHA`. Definir una variable solo en PowerShell no prueba que Railway la reciba. Cualquier ajuste de metadata del proveedor debe estar incluido expresamente en la aprobacion de ejecucion; no cambiar secretos ni configuracion funcional.

5. Verificar backend antes de web:
   ```powershell
   Invoke-RestMethod "$rollbackApiUrl/health" -Headers @{"X-Request-Id"="rollback_health_<timestamp>"} -TimeoutSec 15
   Invoke-RestMethod "$rollbackApiUrl/ready" -Headers @{"X-Request-Id"="rollback_ready_<timestamp>"} -TimeoutSec 15
   Invoke-RestMethod "$rollbackApiUrl/api/v1/version" -Headers @{"X-Request-Id"="rollback_version_<timestamp>"} -TimeoutSec 15
   ```
   Exigir HTTP 200, `data.build_id` igual al SHA destino, `data.environment=staging` en version y readiness disponible. Si no coincide, no desplegar web.

6. Redeploy frontend staging desde el mismo worktree/SHA:
   ```powershell
   $env:NEXT_PUBLIC_API_BASE_URL="https://nodo-api-production.up.railway.app"
   $env:NEXT_PUBLIC_APP_URL="https://nodo-staging.pages.dev"
   $env:NEXT_PUBLIC_APP_ENV="staging"
   $env:NODO_RELEASE_COMMIT_SHA="<previous_full_sha>"
   $env:CLOUDFLARE_PAGES_PROJECT_NAME="nodo-staging"
   $env:CLOUDFLARE_PAGES_BRANCH="staging"
   corepack pnpm deploy:web:staging
   ```
   El script exige arbol limpio e identidad backend/web coincidente. Tambien realiza un POST de autenticacion con initData invalido como smoke; no es una comprobacion exclusivamente read-only.

7. Validar:
   ```powershell
   Invoke-RestMethod "$rollbackApiUrl/health" -Headers @{"X-Request-Id"="rollback_health_<timestamp>"} -TimeoutSec 15
   Invoke-RestMethod "$rollbackApiUrl/ready" -Headers @{"X-Request-Id"="rollback_ready_<timestamp>"} -TimeoutSec 15
   Invoke-RestMethod "$rollbackApiUrl/api/v1/version" -Headers @{"X-Request-Id"="rollback_version_after_<timestamp>"} -TimeoutSec 15
   Invoke-RestMethod "$rollbackWebUrl/version.json?rollback=<short_sha>" -Headers @{"Cache-Control"="no-cache"} -TimeoutSec 15
   ```

8. Para un simulacro, regresar al SHA inicial aprobado usando otro worktree limpio, el mismo orden backend-first y las mismas verificaciones. No declarar el simulacro completado hasta verificar el regreso y el smoke de Admin/Telegram.

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

DOCUMENTED / NOT VALIDATED IN STAGING. Este corte no aporta evidencia de un rollback ejecutado. El redeploy de una version nueva no demuestra un rollback ni su regreso. Produccion abierta sigue bloqueada hasta completar la evidencia de recuperacion y compatibilidad DB/storage.
