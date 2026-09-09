# SOP: Deployment

SOP_ID: SOP-DEPLOY-001
Estado de validacion: PARTIALLY VALIDATED
Ultima revision documental: 2026-09-09
Esta revision no registra un nuevo deploy ni una nueva validacion en proveedor.

## Proposito

Preparar y verificar un despliegue de NODO sin romper servicios Tier 0/Tier 1.

## Alcance

Backend Railway y frontend Cloudflare Pages. El frontend staging tiene comando versionado con guardrails. Backend Railway usa procedimiento CLI proveedor, no script propio del repo.

## Tier afectado

Tier 0/1.

## Cuando utilizarlo

Antes de desplegar staging o produccion.

## Cuando no utilizarlo

Durante un SEV-1 activo salvo que el Incident Commander apruebe rollback/deploy mitigador.

## Riesgos

- Deploy backend incompatible con DB.
- Frontend apuntando a API incorrecta.
- Secret faltante.
- Rollback provider no automatizado.

## Permisos requeridos

- Acceso al proveedor de deploy.
- Acceso solo lectura a repo.
- Aprobacion owner para produccion.

## Prerrequisitos

- Worktree revisado.
- Variables documentadas en `control_plane/11_OPERATIONS/ENVIRONMENT_VARIABLES.md`.
- Migraciones staging validadas si hay cambios DB.

## Herramientas necesarias

- Python.
- Corepack pnpm.
- Proveedor Railway/Cloudflare.
- Para frontend staging: `scripts/deploy_cloudflare_pages_staging.py`.

## Procedimiento

1. Ejecutar validaciones locales:
   ```powershell
   python -m pytest apps\api\tests -q
   python -m ruff check apps\api scripts
   python -m compileall apps\api apps\web\src scripts
   corepack pnpm --filter @nodo/web build
   ```
   Resultado esperado: todos pasan.

2. Si cambiaron dependencias frontend:
   ```powershell
   corepack pnpm audit --prod
   ```
   Resultado esperado: no known vulnerabilities.

3. Verificar que no hay secretos en frontend/source/build:
   ```powershell
   rg -n "BOT_TOKEN|BUSINESS_INTAKE_BOT_TOKEN|SUPABASE_SERVICE_ROLE_KEY|DATABASE_URL|REDIS_URL|PRIVATE_KEY|seed phrase|storage_path|account_value" apps/web apps/api scripts
   ```
   Resultado esperado: solo apariciones permitidas como prohibiciones/docs o ninguna en bundle.

4. Preparar las variables publicas para el build staging posterior al backend:
   ```powershell
   $env:NEXT_PUBLIC_API_BASE_URL="https://nodo-api-production.up.railway.app"
   $env:NEXT_PUBLIC_APP_URL="https://nodo-staging.pages.dev"
   $env:NEXT_PUBLIC_APP_ENV="staging"
   $env:NODO_RELEASE_COMMIT_SHA=(git rev-parse HEAD).Trim()
   ```
   No ejecutar todavia `build:web:staging`: ese comando consulta el backend activo y exige el mismo SHA. La compilacion local del paso 1 es independiente de esa comparacion remota.

5. Para backend Railway staging, usar el procedimiento CLI aprobado para el proyecto actual despues de validar target y SHA:
   ```powershell
   railway up --ci --service nodo-api --environment production --project cf196334-9990-440e-8eb3-c519e4fcdf37 --message "<release message>"
   ```
   Resultado esperado: el deploy termina y `/health` mas `/api/v1/version` reportan el SHA aprobado.
   El worktree fuente debe estar limpio y corresponder al SHA aprobado. Verificar antes que la metadata de release del runtime Railway corresponde a ese SHA; una variable local PowerShell no configura por si sola el runtime remoto. El target historico llamado `production` debe verificarse como staging por proyecto, dominio y ambiente de la API.

6. Para desplegar frontend staging despues de backend verificado:
   ```powershell
   $env:NEXT_PUBLIC_API_BASE_URL="https://nodo-api-production.up.railway.app"
   $env:NEXT_PUBLIC_APP_URL="https://nodo-staging.pages.dev"
   $env:NEXT_PUBLIC_APP_ENV="staging"
   $env:NODO_RELEASE_COMMIT_SHA=(git rev-parse HEAD).Trim()
   $env:CLOUDFLARE_PAGES_PROJECT_NAME="nodo-staging"
   $env:CLOUDFLARE_PAGES_BRANCH="staging"
   corepack pnpm deploy:web:staging
   ```
   Resultado esperado: el script vuelve a construir/verificar, exige worktree limpio y ejecuta Cloudflare Pages contra `nodo-staging` rama `staging`.

7. Ejecutar post deploy:
   Ver `POST_DEPLOY_VERIFICATION_SOP.md`.

## Criterio de exito

- Build/tests pasan.
- Health/ready/version pasan en el entorno desplegado.
- Smoke critico pasa.
- Evidencia guardada.

## Criterio de aborto

- Falla test.
- Falla migracion.
- Falla readiness.
- Secret aparece en bundle/log/API.

## Rollback

Usar `ROLLBACK_SOP.md`.

## Evidencia

Guardar comandos y resultados en `operations/evidence/`.

## Escalamiento

Owner tecnico: OWNERSHIP NOT DEFINED - RELEASE RISK.
