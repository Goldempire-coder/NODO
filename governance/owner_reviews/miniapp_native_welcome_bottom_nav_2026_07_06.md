# MINIAPP_NATIVE_WELCOME_BOTTOM_NAV - 2026-07-06

## Estado

`STAGING_DEPLOYED_FOR_OWNER_REVIEW`

No se declara `READY_FOR_REAL_USE`.

## Motivo

El owner reportó que la Mini App:

- se veía genérica;
- no tenía página de welcome;
- no tenía términos;
- repetía demasiado `Cambio verificado`;
- no tenía botones inferiores de acceso rápido;
- mostraba admin dentro de la app móvil cuando el admin debe ser un panel web separado para PC.

## Cambios aplicados

- Mini App autenticada entra primero en `welcome`.
- Se agregó vista `terms`.
- Se agregó bottom navigation fijo:
  - `Inicio`
  - `Órdenes`
  - `Negocio`
- Se removió `Admin` de la navegación móvil.
- `isAdminSurface` queda desactivado en la Mini App.
- `AdminConsoleScreens` ya no se renderiza desde el shell móvil.
- El header superior dejó de repetir `Cambio verificado` en marketplace.
- Se reemplazó el check textual del logo por dibujo CSS para evitar mojibake en Telegram/iOS.
- Se reemplazaron íconos textuales `?`/check por `status-dot` CSS.
- Se ajustó el layout para evitar textos verdes colapsados en columnas.

## Archivos tocados

- `apps/web/src/types/domain.ts`
- `apps/web/src/hooks/workspace/useWorkspaceState.ts`
- `apps/web/src/hooks/workspace/useTelegramNativeShell.ts`
- `apps/web/src/screens/auth/AuthEntryPage.tsx`
- `apps/web/src/screens/business/WorkspaceShell.tsx`
- `apps/web/src/screens/business/RemitterScreens.tsx`
- `apps/web/src/components/nodo/AnimatedLogo.tsx`
- `apps/web/src/app/globals.css`

## Validación

- Frontend build: `PASS`
- Secret scan build: `PASS`
- Backend ready:
  - database OK
  - redis OK
- Cloudflare deploy:
  - preview: `https://d45324e2.nodo-staging.pages.dev`
  - main alias: `https://nodo-staging.pages.dev`
- Bundle publicado:
  - backend Railway presente
  - welcome presente
  - términos presente
  - bottom nav presente
  - admin nav no presente
  - secretos no presentes

## Pendiente

- Crear panel admin web separado para escritorio/PC.
- Definir ruta/admin auth del panel web fuera de Telegram Mini App.
- Smoke real en Telegram después de cerrar/reabrir `@NodoCambioBot`.
- Seed real de negocios/anuncios para ver marketplace con cards reales.
