# Mini App welcome, terms and client shell fix

Fecha: 2026-07-06

Estado: STAGING_DEPLOYED_FOR_OWNER_REVIEW

No se declara READY_FOR_REAL_USE.

## Cambios

- Primera entrada: welcome con `Bienvenido a NODO` y boton `Comenzar`.
- Terminos: `Acepto y continuar` llama backend y registra aceptacion.
- Usuarios que ya aceptaron terminos entran directo a marketplace.
- Mini App cliente: barra inferior queda `Inicio`, `Ordenes`, `Perfil`.
- Se retira `Negocio` de la barra inferior de cliente para no inducir auto-registro.
- Admin no se expone en el shell de Mini App cliente.
- Disclaimer de responsabilidad deja de aparecer como banner global; queda en detalle/creacion de orden.
- Nombres tecnicos largos de smoke/concurrency no rompen tarjetas de negocio.
- Favicon/icono `N + check` agregado.
- Animaciones de logo/check y botones reducidas para sentirse mas fluidas.

## Backend

- Migracion nueva: `database/migrations/0012_terms_acceptance.up.sql`.
- Columnas nuevas en `users`:
  - `terms_accepted_at`
  - `terms_version`
- Endpoint nuevo:
  - `POST /api/v1/users/me/terms-acceptance`
- Audit event:
  - `terms_accepted`

## Evidencia

- Supabase staging migration:
  - `evidence/slice_runs/supabase_staging_terms_migration_20260706.json`
  - Resultado: `columns = ["terms_accepted_at", "terms_version"]`, failures `[]`.
- Staging terms smoke:
  - `evidence/slice_runs/staging_terms_acceptance_smoke_20260706.json`
  - Resultado: login `200`, accept `200`, users/me `200`, terms accepted `true`, telegram_id not exposed.

## Deploy

- Backend Railway redeployed:
  - URL: `https://nodo-api-production.up.railway.app`
  - Deployment ID: `98637499-0ced-4f97-9287-f379cabba4a6`
  - `/ready`: database OK, redis OK.
- Frontend Cloudflare Pages redeployed:
  - Canonical: `https://nodo-staging.pages.dev`
  - Preview: `https://fbdeb988.nodo-staging.pages.dev`

## Verificacion

- `corepack pnpm --filter @nodo/web build`: OK.
- `python -m pytest apps/api/tests -q`: 100 passed, 1 warning conocido Starlette/httpx.
- `python -m ruff check apps/api scripts`: OK.
- `python -m compileall apps scripts`: OK.
- Published JS checks:
  - API URL presente.
  - `Perfil` presente.
  - endpoint `/api/v1/users/me/terms-acceptance` presente.
  - `Bienvenido a NODO` presente.
  - nav cliente `Negocio` no presente.
  - disclaimer global `NODO no recibe, retiene ni transfiere fondos de usuarios.` no presente.
- Frontend secret scan:
  - sin hits para server secrets, URLs privadas, `storage_path` o `account_value`.

## Pendiente

- Owner debe abrir Telegram y validar visualmente la Mini App publicada.
- No autorizar uso real hasta smoke manual completo y aprobacion explicita.
