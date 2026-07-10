# Evidence - slice_14C_admin_web_surface

## Estado

READY_FOR_OWNER_REVIEW

## Fecha

2026-07-07T19:00:22.9065838-04:00

## Implementacion verificada

- Admin Web separado por `?surface=admin`.
- `AuthEntryPage` monta `AdminWebWorkspace` fuera de `AppRoot`.
- Cliente y negocio conservan sus entradas existentes.
- Admin Web usa sidebar, top bar, tablas, filtros, busqueda, paginacion conceptual y paneles de detalle.
- Mutaciones criticas pasan por confirmacion visual con reason e idempotency.

## Archivos principales

- `apps/web/src/hooks/useAdminWebModel.ts`
- `apps/web/src/screens/admin-web/AdminWebWorkspace.tsx`
- `apps/web/src/screens/admin-web/AdminWebShell.tsx`
- `apps/web/src/screens/admin-web/AdminWebScreens.tsx`
- `apps/web/src/screens/auth/AuthEntryPage.tsx`
- `apps/web/src/app/globals.css`

## Comandos ejecutados

```powershell
corepack pnpm --filter @nodo/web build
```

Resultado: OK. Next.js 15.5.20 compilo y exporto correctamente. Ruta `/`: 32.2 kB, First Load JS 135 kB.

```powershell
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
```

Resultado: OK. `105 passed, 1 warning in 13.77s`.

```powershell
python -m ruff check apps\api scripts
```

Resultado: OK. `All checks passed!`.

```powershell
python -m compileall apps scripts
```

Resultado: OK.

## Scans ejecutados

```powershell
rg -n "ClientWorkspace|BusinessMiniAppWorkspace|RemitterScreens|VerificationScreens|BusinessOperationsScreens|BusinessWorkspaceModel" apps\web\src\screens\admin-web apps\web\src\hooks\useAdminWebModel.ts
```

Resultado: OK, sin coincidencias.

```powershell
rg -n "@telegram-apps|MainButton|themeParams|bottom nav|Telegram MainButton" apps\web\src\screens\admin-web apps\web\src\hooks\useAdminWebModel.ts
```

Resultado: OK, sin coincidencias.

```powershell
rg -n "SUPABASE_SERVICE_ROLE_KEY|BOT_TOKEN|JWT_SECRET|JWT_REFRESH_SECRET|storage_path|fondos protegidos|pago garantizado|garantía de entrega|garantia de entrega|NODO recibió dinero|NODO recibio dinero|escrow" apps\web\src apps\web\out
```

Resultado: OK, sin coincidencias.

```powershell
rg -n "account_value" apps\web\src\screens\admin-web apps\web\src\hooks\useAdminWebModel.ts apps\web\out
```

Resultado: OK, sin coincidencias.

## Tests no ejecutados

- Runner especifico 14C: no existe script `slice_14C` en `scripts`. Se cubrio con validaciones equivalentes obligatorias.
- Deploy: fuera de scope por instruccion del owner.

## Riesgos residuales

- Falta definir/aprobar ruta o dominio final para Admin Web si no se quiere mantener `?surface=admin`.
- Falta smoke visual manual/browser real del panel admin.
- No es `READY_FOR_REAL_USE`.
