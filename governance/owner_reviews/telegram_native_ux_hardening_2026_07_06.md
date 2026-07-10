# telegram_native_ux_hardening_2026_07_06

Estado: TELEGRAM_NATIVE_UX_PARTIAL_HARDENING_READY_FOR_TELEGRAM_SMOKE

Fecha: 2026-07-06

## Alcance

Se reforzo la integracion nativa de Telegram Mini App en el frontend.

No se cambiaron endpoints.
No se cambiaron payloads.
No se cambio copy/disclaimers de negocio.
No se cambio backend.
No se hizo deploy.
No se probo dentro de Telegram real.
No se declaro `READY_FOR_REAL_USE`.

## Archivos modificados

```txt
apps/web/src/theme/telegramTheme.ts
apps/web/src/hooks/useTelegramAuth.ts
apps/web/src/hooks/useBusinessWorkspaceModel.ts
apps/web/src/hooks/workspace/useTelegramMainButton.ts
apps/web/src/hooks/workspace/useTelegramNativeShell.ts
apps/web/src/app/globals.css
```

## Implementado

### Telegram bridge

Se centralizo acceso defensivo a:

```txt
window.Telegram.WebApp
```

Capacidades tipadas:

```txt
ready
expand
disableVerticalSwipes
enableClosingConfirmation
disableClosingConfirmation
BackButton
MainButton
HapticFeedback
themeParams
```

### Viewport nativo

Al iniciar auth/workspace:

```txt
WebApp.ready()
WebApp.expand()
WebApp.disableVerticalSwipes()
```

Todo es opcional/defensivo para no romper navegador normal.

### BackButton nativo

Se agrego `useTelegramNativeShell`.

Reglas:

- root views no muestran BackButton.
- vistas internas muestran BackButton.
- back navega a vista previa si es valida.
- si no hay vista previa util, usa fallback por dominio.

### Closing confirmation

Se activa en vistas con edicion/accion sensible:

```txt
onboarding
verification
create-order
report-payment
create-ad
buy-credits
admin-detail
admin-credit-detail
admin-credit-adjustments
admin-dispute-detail
```

Se desactiva al salir o cuando no aplica.

### Haptic feedback

Implementado:

- success/error/warning durante auth.
- `selectionChanged` al cambiar de vista.
- `impactOccurred("light")` al tocar MainButton.

### MainButton nativo

Mejorado:

- `setText`.
- `setParams` cuando esta disponible.
- `enable/disable`.
- `showProgress/hideProgress`.
- cleanup con `offClick`, `hideProgress` y `hide`.

### Safe areas

CSS actualizado con:

```txt
100dvh
env(safe-area-inset-top)
env(safe-area-inset-right)
env(safe-area-inset-bottom)
env(safe-area-inset-left)
overscroll-behavior: none
```

## Validacion ejecutada

```txt
corepack pnpm --filter @nodo/web build
python -m ruff check apps\api scripts
python -m compileall apps\api scripts
```

Resultado:

```txt
frontend build: OK
ruff: OK
compileall: OK
```

## Riesgos residuales

- Falta smoke dentro de Telegram real.
- Falta validar teclado movil real.
- Falta validar safe areas en iOS/Android real.
- Falta validar BackButton real dentro del cliente Telegram.
- Falta validar MainButton loading/disabled real dentro del cliente Telegram.
- Falta validar theme live updates si Telegram cambia dark/light durante sesion.
- Falta medir si `disableVerticalSwipes` esta disponible en todos los clientes soportados.

## Decision recomendada

```txt
TELEGRAM_NATIVE_UX_PARTIAL_HARDENING_READY_FOR_TELEGRAM_SMOKE
NOT_READY_FOR_REAL_USE
```

## Siguiente paso recomendado

Despues de deploy staging:

1. Abrir NODO desde Telegram real.
2. Validar auth con `initData` real.
3. Validar tema dark/light.
4. Validar BackButton por flujo.
5. Validar MainButton en onboarding, verification, create-order y report-payment.
6. Validar haptics en telefono real.
7. Validar teclado y safe areas en Android/iOS.
