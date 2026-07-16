# slice_34W_business_ads_screen_component_split

Estado final: `READY_FOR_OWNER_REVIEW`

## Objetivo

Reducir el tamano y acoplamiento de la pantalla de anuncios de la Mini App Negocio sin cambiar reglas de negocio, endpoints, migraciones, creditos, Zelle, PIN, infraestructura ni deploy.

## Cambios implementados

- `apps/web/src/screens/business-app/ads/businessAdViewHelpers.ts`
  - Extrae helpers puros de presentacion de anuncios:
    - rango USD
    - tasa
    - fechas
    - etiqueta Zelle
    - permisos visuales para borrar/republicar/reactivar

- `apps/web/src/screens/business-app/ads/BusinessAdCard.tsx`
  - Extrae la tarjeta compacta de anuncio.
  - Mantiene botones `Ver`, `Pausar`, `Reactivar`, `Republicar` y `Borrar`.

- `apps/web/src/screens/business-app/ads/BusinessAdDetailPanel.tsx`
  - Extrae el detalle/editor de anuncio.
  - Mantiene seleccion de Zelle activo, edicion de tasa/rango y acciones sensibles.

- `apps/web/src/screens/business-app/BusinessAdsScreens.tsx`
  - Queda enfocado en pantallas:
    - crear anuncio
    - mis anuncios
    - archivados
    - Zelle
  - Deja de definir helpers, card y detalle internamente.

- `apps/api/tests/test_auth_lifecycle_static.py`
  - Actualiza tests estaticos para proteger la nueva separacion.

## Que NO se toco

- No se cambiaron reglas de credito.
- No se cambio la regla de consumo/archivo/republicacion de anuncios.
- No se cambio comportamiento backend.
- No se cambio API.
- No se cambio DB/migraciones.
- No se hizo deploy.
- No se tocaron secrets, wallets, RPC ni provider config.

## Validacion ejecutada

- `python -m pytest apps/api/tests/test_auth_lifecycle_static.py -q --tb=short` -> `7 passed`
- `python -m pytest apps/api/tests -q` -> `352 passed, 1 warning`
- `python -m compileall apps/api apps/web/src scripts` -> passed
- `python -m ruff check apps/api scripts` -> passed
- `pnpm --filter @nodo/web build` con runtime Node empaquetado -> passed
- `git diff --check` -> passed, solo avisos CRLF/LF existentes

## Riesgos pendientes

- La confirmacion nativa `window.confirm` sigue existiendo para borrar anuncios; debe reemplazarse por modal propio si el equipo quiere UX consistente dentro de Telegram.
- `PaymentMethodsScreen` sigue dentro de `BusinessAdsScreens.tsx`; puede extraerse en un slice posterior.
- No se hizo walkthrough manual en Telegram despues de este refactor.

## Veredicto

`READY_FOR_OWNER_REVIEW`
