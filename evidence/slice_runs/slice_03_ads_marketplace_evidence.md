# slice_03_ads_marketplace evidence

Fecha: 2026-07-04
Estado: READY_FOR_OWNER_REVIEW

## Evidencia tecnica

- Backend modular `ads` implementado en `apps/api/app/modules/ads/`.
- Endpoints autorizados registrados bajo `/api/v1`.
- Migracion reversible creada:
  - `database/migrations/0004_slice_03_ads_marketplace.up.sql`
  - `database/migrations/0004_slice_03_ads_marketplace.down.sql`
- UI minima gobernada integrada en `apps/web/src/app/page.tsx` para:
  - R-02/R-03 marketplace search/results
  - R-04 business detail
  - B-08 create ad
  - B-09 my ads
  - B-10 archived ads
- Resultados JSON generados en `evidence/slice_runs/slice_03_ads_marketplace_test_results.json`.

## Comandos ejecutados

```txt
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_ads_marketplace.py -q
resultado: 11 passed, 1 Starlette/httpx warning.
```

```txt
python scripts\run_slice_03_tests.py
resultado: OK; pytest slice 03 11 passed, compileall OK, frontend secret/private-data scan OK.
```

```txt
corepack pnpm --filter @nodo/web build
resultado: OK; Next.js compiled and type-checked.
```

```txt
python scripts\run_slice_00_tests.py
resultado: passed 6, failed 0.
```

```txt
python scripts\run_slice_01_tests.py
resultado: passed 6, failed 0.
```

```txt
python scripts\run_slice_02_tests.py
resultado: OK; pytest slice 02 9 passed, compileall OK, scan OK.
```

```txt
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
resultado: 35 passed, 1 Starlette/httpx warning.
```

```txt
python -m ruff check apps\api scripts
resultado: All checks passed.
```

```txt
python -m compileall apps/api scripts
resultado: OK.
```

```txt
rg -n "BOT_TOKEN|JWT_SECRET|JWT_REFRESH_SECRET|owner@example\.com|storage_path|account_value|BEGIN PRIVATE KEY|AKIA[0-9A-Z]{16}" apps\web\src apps\web\.next
resultado: no matches.
```

## Contratos verificados

- `ad.status` usa solo `draft`, `active`, `in_order`, `paused`, `expired`, `archived`, `suspended`.
- Crear anuncio publica directo como `active`, con `activated_at = now()` y `expires_at = activated_at + 7 days`.
- Solo negocio `approved` y no `restricted/high_risk` puede publicar y aparecer en marketplace.
- Owner solo muta anuncios de su propio negocio.
- Payment method debe pertenecer al negocio, estar `approved` y `active`.
- `required_credits` se calcula por `amount_max_usd`: 1/2/3 y bloquea `> 2000`.
- Publicar con credito hace hold: decrementa available, incrementa blocked, crea `credits_ledger.type = hold`.
- Founder access vigente permite publicar sin debitar creditos y registra ledger `founder_free_use`.
- Search solo devuelve anuncios efectivos `active`, no vencidos, de negocios aprobados.
- Detail/click no consume creditos.
- Pause no extiende `expires_at` ni libera creditos.
- Archive permitido desde `paused` o `expired`; libera hold cuando aplica.
- Expiracion pasiva materializa `expired`, audita `ad_expired` y libera hold sin orden/pago.
- Ledger es append-only en el flujo implementado.
- Idempotencia aplicada a create/update/pause/archive con namespace por accion.
- Rate limit aplicado a search, detail y mutaciones de ads.
- Audit events implementados: `ad_created`, `ad_published`, `ad_updated`, `ad_paused`, `ad_archived`, `ad_expired`, `credits_held`, `credits_released`.
- UI usa Telegram UI kit existente, theme params heredados, safe shell del entry y no crea landing comercial.
- Frontend no expone `account_value`, `storage_path`, secrets ni datos privados completos.

## Riesgos residuales

- Migraciones reales contra PostgreSQL/Supabase siguen pendientes hasta contar con servicio/credenciales.
- Readiness success contra Redis real sigue pendiente hasta contar con servicio/credenciales.
- Storage privado real sigue pendiente; slice 03 no agrega runtime storage nuevo.
- La prueba de migracion valida contenido contractual, no aplica DDL contra PostgreSQL real.
- Warning Starlette/httpx en TestClient se mantiene como riesgo aceptado temporalmente.
- Smoke manual dentro de Telegram real no ejecutado en esta corrida.

## Estado

READY_FOR_OWNER_REVIEW
