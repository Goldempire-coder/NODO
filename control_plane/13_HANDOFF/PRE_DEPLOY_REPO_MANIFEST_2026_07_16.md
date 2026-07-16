# PRE_DEPLOY_REPO_MANIFEST_2026_07_16

Estado: `REPO_RELEASE_CANDIDATE_VALIDATED_READY_FOR_COMMIT`

Fecha de inspeccion: 2026-07-16.

Branch observado: `codex/cloud-scalability-cost-runner`.

HEAD observado: `55bc35b`.

Este documento no autoriza deploy. Su objetivo es dejar el repo organizado y evitar un despliegue desde un working tree ambiguo.

## Resultado Ejecutivo

El repo ya no tiene archivos runtime sin trackear ni cambios sueltos fuera del candidato staged.

Resultado actual despues de validacion:

| Check | Resultado |
|---|---:|
| `git status --short` | 524 entradas staged |
| `git diff --name-only` | 0 entradas |
| `git diff --cached --name-only` | 524 entradas |
| `git ls-files --others --exclude-standard` | 0 entradas |
| `python scripts/predeploy_release_audit.py --json` | `PASS` |
| `python -m pytest apps/api/tests -q` | `359 passed, 1 warning` |
| `python -m ruff check apps/api scripts` | `PASS` |
| `python -m compileall apps/api apps/web/src scripts` | `PASS` |
| `pnpm --filter @nodo/web build` | `PASS` |
| `pnpm audit --prod` | `No known vulnerabilities found` |

Interpretacion:

- El release candidate esta organizado en stage.
- No hay runtime importado fuera del paquete staged.
- No hay evidencia de secretos bloqueantes en el candidato revisado.
- La validacion local completa paso.
- No hay deploy ejecutado todavia.

## Auditor Predeploy

Comando:

```powershell
python scripts\predeploy_release_audit.py --json
```

Resultado:

```text
status: PASS
decision: READY_FOR_VALIDATION_COMMANDS
failures: []
untracked_runtime_count: 0
secret_blockers: 0
```

Conteo del auditor:

| Categoria | Cantidad |
|---|---:|
| runtime | 217 |
| tooling | 37 |
| docs | 268 |
| evidence | 0 |
| other | 2 |

Los `secret_warnings` restantes son menciones de terminos sensibles usados por redaccion, tests, scanners o documentacion. No son secretos reales detectados por el auditor.

## Limpieza Aplicada

Se incluyeron en el candidato staged los runtime files que estaban untracked:

- `apps/web/src/hooks/business-mini-app/actionTelemetry.ts`
- `apps/web/src/hooks/business-mini-app/businessPinGuards.ts`
- `apps/web/src/hooks/business-mini-app/useBusinessHomeSummaryModel.ts`
- `apps/web/src/screens/business-app/ads/BusinessAdCard.tsx`
- `apps/web/src/screens/business-app/ads/BusinessAdDetailPanel.tsx`
- `apps/web/src/screens/business-app/ads/businessAdViewHelpers.ts`
- `database/migrations/0023_business_operational_availability.up.sql`
- `database/migrations/0023_business_operational_availability.down.sql`

Tambien se incluyeron los contratos, reportes y owner reviews recientes de Mini App Negocio:

- `control_plane/09_SLICES/slice_35_business_mini_app_afos_hardening/`
- `control_plane/09_SLICES/slice_36_business_mini_app_afos_release_hardening/`
- `governance/builder_reports/slice_34U_business_mini_app_architecture_reliability_hardening_BUILDER_REPORT.md`
- `governance/builder_reports/slice_34V_business_mini_app_clean_architecture_BUILDER_REPORT.md`
- `governance/builder_reports/slice_34W_business_ads_screen_component_split_BUILDER_REPORT.md`
- `governance/builder_reports/slice_34X_business_credit_movements_ui_removal_BUILDER_REPORT.md`
- `governance/builder_reports/slice_34Y_business_credits_purchase_ux_cleanup_BUILDER_REPORT.md`
- `governance/builder_reports/slice_34Z_business_zelle_reliability_cleanup_BUILDER_REPORT.md`
- `governance/builder_reports/slice_35_business_mini_app_afos_hardening_BUILDER_REPORT.md`
- `governance/builder_reports/slice_36_business_mini_app_afos_release_hardening_BUILDER_REPORT.md`
- `governance/builder_reports/business_mini_app_usdt_trc20_payment_methods_alignment_BUILDER_REPORT.md`
- `governance/owner_reviews/business_mini_app_afos_audit_2026_07_16.md`
- `governance/owner_reviews/slice_35_business_mini_app_afos_hardening_owner_audit.md`

## Estado Del Candidato

El candidato staged incluye multiples slices acumulados. No debe tratarse como hotfix pequeno.

Familias principales incluidas:

- Base USDC credit topups.
- Admin users/business control.
- Support ticket center.
- Internal staff roles.
- Backend/frontend observability.
- Staging delivery diagnostics and policy.
- Business Mini App PIN, Zelle/payment methods, ads, credits, orders and support hardening.
- DR/backup contracts and runbooks.

## Bloqueadores Que Ya Quedaron Cerrados

### CERRADO - Runtime Untracked

Antes:

- `UNTRACKED_RUNTIME_FILES`
- 6 runtime entries sin trackear.

Ahora:

- `untracked_runtime_count: 0`
- `git ls-files --others --exclude-standard`: 0 entradas.

### CERRADO - Cambios Sueltos Fuera Del Candidate

Antes:

- `git diff --name-only`: 66 entradas.

Ahora:

- `git diff --name-only`: 0 entradas.

### CERRADO - Secret Blockers En Candidate

Auditor:

- `secret_blockers: 0`

## Bloqueadores Que Siguen Antes De Deploy

### BLOCKER-001 - Owner Approval Required

El repo esta organizado, pero no aprobado para deploy.

Criterio de cierre:

- owner aprueba preparar staging deploy sobre este candidato exacto.

### BLOCKER-002 - Migraciones 0017-0023

El candidato incluye migraciones nuevas hasta:

- `0023_business_operational_availability`

Criterio de cierre:

- correr migraciones en staging segun SOP.
- validar schema post-migration.
- tener rollback/forward-fix definido.
- no tocar produccion.

### BLOCKER-003 - Provider Deploy Steps

El repo no contiene un comando universal automatizado de Railway/Cloudflare para todo el release.

Criterio de cierre:

- ejecutar procedimiento del proveedor.
- registrar build/deployment id.
- correr smoke post-deploy.

### BLOCKER-004 - Mini App Telegram Real Smoke

Las validaciones locales pasan, pero falta smoke real desde Telegram Mini App despues de staging deploy.

Criterio de cierre:

- business login real.
- PIN.
- online/offline.
- Zelle add/edit/delete.
- crear anuncio Zelle-Bs.
- crear anuncio USDT-Bs.
- comprar creditos Base USDC con wallet configurada.
- orden cliente-negocio en slice separado.

## Comandos Requeridos Para Validar Antes De Deploy

```powershell
python scripts\predeploy_release_audit.py
python -m pytest apps/api/tests -q
python -m ruff check apps/api scripts
python -m compileall apps/api apps/web/src scripts
pnpm --filter @nodo/web build
pnpm audit --prod
```

Resultado observado en esta inspeccion:

```text
predeploy_release_audit: PASS
pytest: 359 passed, 1 warning in 86.53s
ruff: All checks passed
compileall: PASS
web build: PASS
pnpm audit --prod: No known vulnerabilities found
```

## Decision

`READY_FOR_COMMIT`

El repo esta organizado y validado localmente. El siguiente paso seguro es crear commit del candidato exacto. Deploy staging sigue requiriendo procedimiento de proveedor, migraciones staging y smoke post-deploy.
