# OWNER AUDIT - slice_14C_admin_web_surface

## Estado

BLOCKED_BY_SECURITY_GAP

## Resultado corto

El builder construyo una superficie visualmente desktop para Admin Web y las validaciones tecnicas base pasan, pero no acepto el slice como listo para owner review funcional porque el acceso al panel admin sigue dependiendo de `useTelegramAuth` y no existe implementacion backend de `GET /api/v1/surface/session`.

Esto significa que el panel puede verse separado por `?surface=admin`, pero todavia no queda cerrado como Admin Web real para usar desde PC fuera de la Mini App.

## Evidencia verificada

- `apps/web/src/screens/auth/AuthEntryPage.tsx` importa `@telegram-apps/telegram-ui`.
- `apps/web/src/screens/auth/AuthEntryPage.tsx` usa `useTelegramAuth()`.
- `apps/web/src/screens/auth/AuthEntryPage.tsx` decide Admin Web solo por `surface === "admin"` despues de autenticacion.
- `apps/api/app` no implementa ruta `/api/v1/surface/session`.
- `control_plane/06_API_CONTRACTS/SURFACE_SESSION_API.md` si define `GET /api/v1/surface/session`.
- `control_plane/05_SECURITY/RBAC_PERMISSION_MATRIX.md` define `access_admin_web`.
- `control_plane/02_ARCHITECTURE/ADMIN_WEB_ARCHITECTURE.md` exige Admin Web separado y auth/session segura.

## Validaciones ejecutadas

```txt
corepack pnpm --filter @nodo/web build
Resultado: OK

$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
Resultado: 105 passed, 1 warning

python -m ruff check apps\api scripts
Resultado: OK

python -m compileall apps scripts
Resultado: OK
```

## Lo que si esta bien

- Existe `apps/web/src/screens/admin-web/`.
- `AdminWebWorkspace`, `AdminWebShell` y `AdminWebScreens` no importan `ClientWorkspace`, `BusinessMiniAppWorkspace`, `RemitterScreens`, `VerificationScreens`, `BusinessOperationsScreens` ni `AdminConsoleScreens`.
- El panel autenticado no esta envuelto en `AppRoot`.
- El modelo `useAdminWebModel` envia `X-NODO-Surface: admin_web` en requests admin.
- El layout tiene sidebar, topbar, tablas, filtros basicos y split panels.
- Mutaciones criticas usan reason en frontend y `Idempotency-Key` en approve/reject/resolve/adjust.
- `support` queda read-only en el frontend para acciones criticas.

## Bloqueo principal

### Admin Web no tiene auth/gate web propio

El contrato pide Admin Web separado. Pero hoy la ruta admin se alcanza asi:

```txt
/?surface=admin
```

y pasa por:

```txt
useTelegramAuth()
```

Eso requiere initData de Telegram. En navegador desktop normal, el panel admin no tiene un flujo de login web/admin propio y puede quedar bloqueado con el mensaje de abrir desde Telegram.

## Riesgo

Si se despliega asi, se puede confundir "layout desktop" con "Admin Web listo". No lo esta. Falta cerrar la entrada segura del admin:

- implementar `GET /api/v1/surface/session`, o
- contratar e implementar login admin web seguro, o
- declarar explicitamente que Admin Web MVP solo abre desde Telegram Desktop con initData, si el owner acepta ese limite temporal.

## Recomendacion

Antes de avanzar a build/deploy real del Admin Web, crear una fase pequena:

```txt
slice_14C1_admin_web_auth_gate
```

Objetivo:

- cerrar contrato de acceso Admin Web real;
- implementar surface/session o auth admin web segura;
- validar `admin_web` en backend;
- evitar que admin dependa implicitamente del flujo Mini App Cliente;
- mantener `support` read-only y mutaciones admin con reason/idempotencia/audit.

## Estado final

BLOCKED_BY_SECURITY_GAP

