# slice_34T_business_mini_app_security_observability_architecture

Estado final: `READY_FOR_OWNER_REVIEW`

## Objetivo

Endurecer la Mini App Negocio sin mezclar responsabilidades:

- mover captura de evidencia frontend a un modulo dedicado;
- agregar endpoint backend de ingesta de observabilidad con auth, superficie y redaccion;
- mantener la ingesta desactivada por defecto;
- no tocar reglas de negocio, wallet privada, deploy ni produccion.

## Scope ejecutado

- Backend observability ingest:
  - `POST /api/v1/observability/events`
  - requiere JWT valido
  - requiere `X-NODO-Surface`
  - bloqueado si `OBSERVABILITY_INGEST_ENABLED` no esta activo
  - rechaza lotes y eventos sobre limites configurados
  - no persiste en DB
  - escribe log estructurado y redaccionado

- Frontend business mini app:
  - extraccion de headers/correlation/request/operation IDs a modulo de telemetria
  - breadcrumbs locales de cambio de pantalla
  - reporte opcional de errores API
  - no captura formularios, tokens, wallet, Zelle, PIN, OTP, tx hash completo ni storage paths

## Non-scope

- No migrar sesiones a cookies HttpOnly.
- No activar observability ingest en staging.
- No cambiar CSP para quitar `unsafe-inline`; Next static export actual genera scripts inline.
- No limpiar todo el repo ni borrar artefactos de slices anteriores.
- No deploy.
- No produccion.

## Riesgos reducidos

- Errores de Mini App Negocio ahora pueden tener request/correlation/operation IDs desde frontend.
- Fallas de API pueden reportarse de forma estructurada si el owner activa el flag.
- Los eventos no confian en `user_id` enviado por cliente; el backend usa el JWT.
- La metadata sensible se redacciona en frontend y backend.
- La logica de observabilidad ya no vive mezclada dentro de `api/client.ts`.

## Riesgos pendientes

- `OBSERVABILITY_INGEST_ENABLED` queda apagado hasta decision owner.
- CSP fuerte requiere cambio separado por scripts inline de Next export.
- Session replay estructurado completo todavia no persiste eventos ni tiene panel admin.
- Sesiones HttpOnly requieren redisenar el contrato auth/web.
- Refactor fino de busy/per-action loading queda para otro slice.

## Validaciones

- `python -m pytest apps\api\tests\test_frontend_observability_ingest.py apps\api\tests\test_auth_lifecycle_static.py -q --tb=short` -> `12 passed, 1 warning`
- `python -m pytest apps\api\tests -q` -> `350 passed, 1 warning`
- `python -m ruff check apps/api scripts` -> passed
- `python -m compileall apps/api apps/web/src scripts` -> passed
- `apps\web\node_modules\.bin\next.CMD build apps\web` con Node PATH explicito -> passed
- scan de secretos/sensibles sobre archivos tocados -> sin wallet real, RPC Coinbase, private keys ni tokens reales

## Confirmaciones

- No agregue secretos.
- No expuse IP address.
- No registre tokens.
- No registre PIN/OTP.
- No registre wallet completa como diagnostico.
- No hice deploy.
- No toque produccion.
- No declare `READY_FOR_REAL_USE`.
