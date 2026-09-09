# CHANGE_MANAGEMENT

Estado: OFFICIAL
Ultima actualizacion: 2026-09-09

## Regla

Ningun cambio se considera listo solo porque compila. Debe tener evidencia de build, tests, seguridad, migraciones si aplica, rollback y operacion.

Para piloto controlado, el resultado maximo permitido es `READY_FOR_OWNER_REVIEW`. Produccion abierta requiere el gate completo de `control_plane/10_QA/DEPLOY_READINESS_GATE.md`.

## Antes de cambiar staging

1. Confirmar slice o ticket.
2. Revisar `control_plane/00_GOVERNANCE/ENGINEERING_GUARDRAILS.md`.
3. Ejecutar:
   ```powershell
   python -m pytest apps\api\tests -q
   python -m ruff check apps\api scripts
   python -m compileall apps\api apps\web\src scripts
   corepack pnpm --filter @nodo/web build
   ```
4. Si toca dependencias frontend:
   ```powershell
   corepack pnpm audit --prod
   ```
5. Si toca DB staging, usar solo scripts con guardrails.

## Deploy staging

Frontend staging tiene script versionado:

```powershell
$env:NEXT_PUBLIC_API_BASE_URL="https://nodo-api-production.up.railway.app"
$env:NEXT_PUBLIC_APP_URL="https://nodo-staging.pages.dev"
$env:NEXT_PUBLIC_APP_ENV="staging"
$env:NODO_RELEASE_COMMIT_SHA=(git rev-parse HEAD).Trim()
corepack pnpm deploy:web:staging
```

Backend Railway sigue sin script propio versionado, pero el procedimiento de staging usado para releases manuales es:

```powershell
railway up --ci --service nodo-api --environment production --project cf196334-9990-440e-8eb3-c519e4fcdf37 --message "<release message>"
```

Antes del deploy web, `/health` y `/api/v1/version` deben reportar el SHA exacto del backend aprobado. Si no coinciden, no desplegar web salvo aprobacion Owner explicita de bypass web-only.

## Rollback

Rollback provider por UI/API Railway/Cloudflare no esta automatizado en repo. Para staging, el rollback minimo documentado es redeploy de un SHA anterior conocido, sin migraciones incompatibles, usando el mismo orden backend-first y luego web. Ver `sops/ROLLBACK_SOP.md`.
