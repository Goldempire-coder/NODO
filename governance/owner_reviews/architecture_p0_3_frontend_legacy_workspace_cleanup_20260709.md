# Architecture P0.3 Repair - Frontend Legacy Workspace Cleanup

## Estado

PASSED_AFTER_FIX

## Problema reparado

El backend ya bloqueaba los endpoints legacy de self-onboarding/verificacion de negocio, pero el frontend todavia conservaba un workspace mixto viejo con pantallas y hooks que llamaban:

- `POST /api/v1/businesses`
- `PUT /api/v1/businesses/{id}`
- `POST /api/v1/businesses/{id}/verification-documents`
- `POST /api/v1/businesses/{id}/submit-verification`

Aunque ya no estaban conectados desde `AuthEntryPage`, seguian dentro de `apps/web/src`, compilables y faciles de reactivar por error.

## Decision aplicada

Retirar del source activo el workspace mixto legacy y sus hooks.

Se mantienen solo las superficies actuales:

- Mini App Cliente
- Mini App Negocio
- Admin Web

## Archivos eliminados

- `apps/web/src/hooks/useBusinessWorkspaceModel.ts`
- `apps/web/src/hooks/workspace/useBusinessVerificationModel.ts`
- `apps/web/src/hooks/workspace/useMarketplaceModel.ts`
- `apps/web/src/hooks/workspace/useBusinessOrderOpsModel.ts`
- `apps/web/src/hooks/workspace/useCreditsReferralsModel.ts`
- `apps/web/src/hooks/workspace/useChatDisputesModel.ts`
- `apps/web/src/hooks/workspace/useAdminConsoleModel.ts`
- `apps/web/src/hooks/workspace/useTelegramMainButton.ts`
- `apps/web/src/hooks/workspace/useTelegramNativeShell.ts`
- `apps/web/src/hooks/workspace/useWorkspaceState.ts`
- `apps/web/src/screens/business/BusinessWorkspace.tsx`
- `apps/web/src/screens/business/WorkspaceShell.tsx`
- `apps/web/src/screens/business/VerificationScreens.tsx`
- `apps/web/src/screens/business/BusinessOperationsScreens.tsx`
- `apps/web/src/screens/business/AdminConsoleScreens.tsx`
- `apps/web/src/constants/navigation.ts`
- `apps/web/src/constants/views.ts`

## Archivos ajustados

- `apps/web/src/hooks/workspace/useRemitterOrdersModel.ts`
- `apps/web/src/hooks/workspace/usePaymentReportModel.ts`
- `apps/web/src/types/domain.ts`
- `apps/api/tests/test_admin_console.py`

## Evidencia de codigo

- `apps/web/src/hooks/workspace/useRemitterOrdersModel.ts:5` ahora depende de `ClientWorkspaceState`, no del workspace mixto.
- `apps/web/src/hooks/workspace/usePaymentReportModel.ts:4` ahora depende de `ClientWorkspaceState`, no del workspace mixto.
- `apps/web/src/types/domain.ts:2` ya no incluye vistas legacy `onboarding`, `verification`, `pending`, `admin-list` ni `admin-detail`.
- `apps/web/src/screens/business` quedo vacio.
- `apps/web/src/hooks/workspace` conserva solo hooks activos de cliente.

## Validacion ejecutada

```txt
rg -n 'useBusinessWorkspaceModel|BusinessWorkspace|WorkspaceShell|VerificationScreens|BusinessOperationsScreens|AdminConsoleScreens|useBusinessVerificationModel|/api/v1/businesses|submit-verification|verification-documents|onboarding|admin-list|admin-detail' apps\web\src
OK: solo queda `verification-documents` en Admin Web para endpoint admin autorizado.

corepack pnpm --filter @nodo/web build
OK

$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
133 passed, 1 warning

python -m ruff check apps\api scripts
All checks passed

python -m compileall apps\api scripts
OK
```

## Alcance no tocado

- No cambie reglas de creditos.
- No cambie lifecycle de ordenes.
- No cambie bot intake.
- No cambie Mini App Cliente.
- No cambie Mini App Negocio.
- No cambie Admin Web funcional.
- No hice deploy.
- No declare `READY_FOR_REAL_USE`.

## Siguiente punto recomendado

P1.1: separar tipos por superficie (`ClientView`, `BusinessMiniAppView`, `AdminWebView`) en vez de seguir usando `BusinessView` como union global compartida. Esto no es agujero funcional, pero mejora la arquitectura para escalar sin mezclar superficies.
