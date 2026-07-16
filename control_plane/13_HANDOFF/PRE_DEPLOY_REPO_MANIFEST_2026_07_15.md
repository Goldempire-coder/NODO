# PRE_DEPLOY_REPO_MANIFEST_2026_07_15

Estado: `REPO_ORGANIZED_READY_FOR_OWNER_REVIEW`

Objetivo: ordenar el estado actual del repo antes de cualquier deploy de NODO.

Este documento no autoriza deploy. Sirve para separar codigo desplegable, migraciones, configuracion, pruebas, documentacion y evidencia.

## Regla Principal

No hacer deploy desde un working tree ambiguo.

Antes de deploy debe existir:

- lista exacta de archivos runtime incluidos
- lista exacta de migraciones incluidas
- lista exacta de variables nuevas o modificadas
- validacion de secretos
- build frontend reproducible
- tests backend ejecutados
- smoke real post-deploy definido
- rollback definido

## Snapshot Del Working Tree

Fecha de inspeccion: 2026-07-15.

Resumen observado con `git diff --name-only` y `git ls-files --others --exclude-standard`:

| Categoria | Cantidad observada |
|---|---:|
| Backend runtime (`apps/api/app`) | 119 |
| Frontend runtime (`apps/web/src`, `apps/web/public`, `next.config`) | 63 |
| Migraciones (`database/migrations`) | 12 |
| Config/env/tooling base | 6 |
| Tests (`apps/api/tests`) | 22 |
| Scripts/workflows | 14 |
| Control plane | 133 |
| Operaciones | 57 |
| Evidencia/reportes | 1289 |

Interpretacion: el repo contiene varios slices acumulados. No debe tratarse como un cambio pequeno ni como hotfix.

## Limpieza No Destructiva Aplicada

Fecha: 2026-07-15.

- Se agrego `scripts/predeploy_release_audit.py`.
- Se actualizo `.gitignore` para excluir evidencia cruda generada en `evidence/slice_runs/` y zips de evidencia.
- La evidencia cruda dejo de ensuciar `git status` sin borrar archivos.
- `git status --short evidence` quedo en 0 lineas observadas.
- `git status --short` bajo de 698 lineas a 329 lineas observadas.
- Los archivos runtime/tooling/docs que forman el release candidate quedaron staged.
- `git diff --name-only` quedo en 0 lineas: no hay cambios pendientes sin stage.
- `git diff --cached --name-only` quedo en 470 lineas: release candidate staged para revision.
- `python scripts\predeploy_release_audit.py` termino en `PASS`.

Esta limpieza no borra evidencia ni autoriza deploy. Solo reduce ruido y deja el release candidate listo para validacion y decision del owner.

## Carriles

### Carril A - Runtime Deploy Candidate

Incluye archivos que pueden afectar la app real:

- `apps/api/app/**`
- `apps/web/src/**`
- `apps/web/public/**`
- `apps/web/next.config.mjs`
- `database/migrations/**`
- `.env.example`
- `.env.local.example`
- `.env.staging.example`
- `Dockerfile`
- `railway.json`
- `package.json`
- `pnpm-lock.yaml`
- `pytest.ini`

Riesgo: alto. Si se despliega incompleto, pueden fallar auth, business mini app, Zelle, Base USDC, soporte, staff, observabilidad o migraciones.

### Carril B - Tests Y Tooling

Incluye:

- `apps/api/tests/**`
- `scripts/**`
- `.github/workflows/**`

Riesgo: medio. No debe romper runtime, pero puede cambiar gates, limpieza staging, carga, capacidad o evidencia.

### Carril C - Governanza Y Operaciones

Incluye:

- `control_plane/**`
- `operations/**`
- `governance/**`

Riesgo: medio. No afecta runtime directo, pero define contratos, SOPs, readiness y restricciones. Debe mantenerse coherente con codigo real.

### Carril D - Evidencia

Incluye:

- `evidence/**`

Riesgo: bajo para runtime, alto para orden del repo. Hay gran volumen de JSON/zips/directorios de pruebas. El backend Docker ya excluye `evidence` por `.dockerignore`, pero Git sigue mostrando mucha evidencia sin trackear.

Decision requerida: definir si se versionan solo summaries finales por slice o tambien artefactos crudos de carga.

## Bloqueadores Antes De Deploy

### BLOCKER-001 - Working Tree No Curado

Hay cientos de archivos modificados/no trackeados. Debe decidirse que entra al deploy y que queda fuera.

Criterio de cierre:

- `git status --short` revisado por carril
- runtime candidate identificado
- evidencia/reportes separados de runtime

### BLOCKER-002 - Migraciones 0017-0022

Existen migraciones nuevas:

- `0017_slice_19_base_usdc_credit_topups`
- `0018_slice_20A_admin_users_business_control`
- `0019_slice_20B_support_ticket_center`
- `0020_slice_20C_internal_staff_roles`
- `0021_business_capacity_limits`
- `0022_business_access_pin`

Criterio de cierre:

- plan de migracion staging confirmado
- rollback/down disponible
- schema validation post-migration ejecutado
- no aplicar produccion sin restore/rollback probado

### BLOCKER-003 - Archivos Runtime No Trackeados

Hay modulos runtime nuevos no trackeados, incluyendo observabilidad, staff, soporte, onchain credits y seguridad PIN.

Riesgo: un deploy parcial puede compilar localmente pero fallar en Railway/Cloudflare si faltan archivos no trackeados.

Ejemplos confirmados de imports runtime que dependen de archivos no trackeados:

- `apps/api/app/main.py` importa:
  - `app.modules.credits.onchain`
  - `app.modules.observability.routes`
  - `app.modules.support.repository`
  - `app.modules.support.routes`
  - `app.modules.staff.repository`
  - `app.modules.staff.routes`
  - `app.shared.observability`
- `apps/api/app/modules/businesses/service.py` importa:
  - `app.modules.businesses.pin_security`
- `apps/web/src/api/client.ts` importa:
  - `apps/web/src/observability/clientTelemetry`
- `apps/web/src/screens/business-app/BusinessMiniAppScreens.tsx` importa:
  - `BusinessPinScreen`
  - `BusinessSupportScreen`
- `apps/web/src/screens/client/ClientScreens.tsx` importa:
  - `ClientSupportScreen`
- `apps/web/src/hooks/useBusinessMiniAppModel.ts` y `apps/web/src/hooks/useClientWorkspaceModel.ts` importan:
  - `useSurfaceSupportModel`

Criterio de cierre:

- todos los runtime imports resueltos desde archivos incluidos
- `git ls-files --others --exclude-standard` revisado para `apps/api/app` y `apps/web/src`
- ningun archivo importado por runtime queda fuera del release candidate

Auditor actual:

```powershell
python scripts\predeploy_release_audit.py
```

Resultado observado:

- `status: FAIL`
- `decision: NO_DEPLOY`
- `failures: UNTRACKED_RUNTIME_FILES`
- `untracked_runtime_count: 43`
- `secret_blockers: 0`

### BLOCKER-004 - Build Web Oficial Inestable

El wrapper actual de `pnpm` puede fallar por politica de build scripts (`sharp approve-builds`). El build directo de Next paso, pero el comando oficial debe quedar estable.

Criterio de cierre:

- comando oficial de build documentado y reproducible
- si se usa `pnpm@9.15.4`, dejarlo explicito en evidencia
- no depender de pasos manuales ocultos

### BLOCKER-005 - Secrets Y Wallets

Se configuro wallet publica Base en Railway. No debe existir private key, seed phrase, API key RPC real ni secrets en repo.

Resultado de inspeccion actual:

- `.env.example`, `.env.local.example` y `.env.staging.example` solo contienen placeholders o valores sinteticos.
- No se encontro el API key RPC real pegado durante configuracion en los archivos candidatos revisados.
- No se encontro endpoint real de Coinbase RPC en los archivos candidatos revisados.
- Los hits amplios de `access_token`, `refresh_token`, `storage_path`, `account_value` y `signed_url` son nombres de campos, tests, docs o scanners. Deben revisarse por contexto, pero no son por si solos evidencia de secreto filtrado.

Criterio de cierre:

- scan repo candidate sin secretos reales
- `.env*` solo examples
- Railway env no copiado a evidencia ni docs

### BLOCKER-006 - Evidencia Y Reportes Mezclados Con Release

El repo contenia 1289 archivos de evidencia/reportes observados entre modificados y no trackeados.

Riesgo: no afecta el Docker backend porque `.dockerignore` excluye `evidence`, pero si se hace commit sin curar el release candidate, el historial puede quedar lleno de artefactos crudos, reportes repetidos y salidas de pruebas no necesarias para operar el codigo.

Mitigacion aplicada:

- `.gitignore` ahora ignora `evidence/slice_runs/`.
- `.gitignore` ahora ignora `evidence/**/*.zip`.
- Los summaries curados deben vivir en documentos oficiales, builder reports o manifests, no como dumps crudos mezclados con runtime.

Criterio de cierre:

- decidir politica de versionado para `evidence/**`
- conservar summaries finales necesarios por slice
- excluir o archivar artefactos crudos que no sean fuente oficial
- no mezclar evidencia masiva con cambios runtime en el mismo paquete de deploy

### BLOCKER-007 - Line Endings Pendientes

Git aviso que multiples archivos modificados cambiaran CRLF a LF cuando se toquen.

Riesgo: diffs ruidosos que dificultan revisar cambios reales antes del deploy.

Criterio de cierre:

- ejecutar formato/line endings de forma controlada o aceptar el cambio en un commit separado
- no mezclar normalizacion masiva con fixes funcionales sensibles

## Checks Requeridos Antes De Deploy

Ejecutar desde `C:\Users\carlo\Documents\Playground\NODO`:

```powershell
python -m pytest apps/api/tests -q
python -m ruff check apps/api scripts
python -m compileall apps/api apps/web/src scripts
```

Build frontend recomendado para este estado local:

```powershell
$env:PATH='C:\Users\carlo\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin;' + $env:PATH
pnpm --filter @nodo/web build
```

Secret scan minimo:

```powershell
rg -n "PRIVATE KEY|seed phrase|mnemonic|api\.developer\.coinbase\.com/rpc|Bearer [A-Za-z0-9._-]+|refresh_token|access_token|account_value|storage_path|signed_url" apps control_plane operations governance scripts .env.example .env.local.example .env.staging.example
```

## Deploy Gate

El deploy queda bloqueado hasta que este documento tenga un owner decision:

- `APPROVED_TO_PREPARE_STAGING_DEPLOY`
- `APPROVED_WITH_LIMITS`
- `REJECTED_PENDING_REPO_CLEANUP`

Estado actual: `REJECTED_PENDING_REPO_CLEANUP`.
Estado actual despues de limpieza: `REPO_ORGANIZED_READY_FOR_OWNER_REVIEW`.

## Orden Recomendado Para Organizar El Repo

1. Crear un release candidate unico de runtime:
   - backend
   - frontend
   - migraciones
   - env examples
   - package/lock/tooling requerido
2. Incluir todos los archivos no trackeados que son importados por runtime.
3. Separar evidencia/reportes en commit o paquete distinto.
4. Ejecutar migraciones en entorno controlado y schema validation.
5. Ejecutar tests/build/secret scan.
6. Solo despues preparar deploy staging.

Estado recomendado para este momento:

`NO_DEPLOY_UNTIL_OWNER_APPROVES_DEPLOY_AND_PROVIDER_STEPS`

## Comando De Bloqueo Actual

```powershell
python scripts\predeploy_release_audit.py
```

Resultado actual despues de limpieza: `PASS`.

Fallas actuales: ninguna.

No avanzar a deploy hasta que el owner apruebe el deploy y se ejecuten los pasos del proveedor sobre este release candidate exacto.
