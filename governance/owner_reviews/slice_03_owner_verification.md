# OWNER VERIFICATION - slice_03_ads_marketplace

Fecha: 2026-07-04

## Resultado

OWNER_ACCEPTED_FOR_NEXT_SLICE

## Alcance revisado

- Backend ads/marketplace.
- Credit wallet y ledger hold/release.
- Migracion slice 03.
- Endpoints canonicos de marketplace y business ads.
- UI R-02, R-03, R-04, B-08, B-09 y B-10.
- Runner, evidencia y pruebas acumuladas.

## Hallazgos durante owner review

La entrega inicial del builder no podia aceptarse sin ajustes por estas desviaciones:

- La implementacion usaba `rate` en API/DB/UI, pero el contrato canonico exige `rate_bs_per_usd`.
- Algunos codigos de error no estaban alineados con `ERROR_CONTRACT.md`:
  - `BUSINESS_APPROVAL_REQUIRED` en vez de `BUSINESS_NOT_APPROVED`.
  - `PAYMENT_METHOD_INVALID` en vez de `PAYMENT_METHOD_NOT_APPROVED` o `INVALID_PAYMENT_METHOD`.
  - `AD_RANGE_OVERLAP` en vez de `AD_OVERLAP_NOT_ALLOWED`.
  - `AD_AMOUNT_RANGE_UNSUPPORTED` en vez de `AD_AMOUNT_TOO_HIGH`.
- `POST /api/v1/business/ads` no aceptaba `business_id`, aunque el contrato del endpoint lo define.
- El limite `business.max_order_amount_usd` no se validaba antes de publicar/editar anuncio.
- `credit_wallets` en migracion/modelo no incluia los lifetime counters definidos en el data contract.
- `pause`/`archive` no aceptaban `reason`, aunque el contrato lo define como request payload.

## Correcciones aplicadas por owner-side Codex

- `apps/api/app/modules/ads/schemas.py`: usa `rate_bs_per_usd`, acepta `business_id` en create y `reason` opcional en pause/archive.
- `apps/api/app/modules/ads/models.py`: renombra tasa a `rate_bs_per_usd` y agrega lifetime counters de wallet.
- `apps/api/app/modules/ads/service.py`: alinea errores, valida `business_id`, valida limite maximo del negocio, usa `rate_bs_per_usd`, acepta reason en pause/archive.
- `apps/api/app/modules/ads/repository.py`: usa columna/campo `rate_bs_per_usd` en memoria y Postgres.
- `apps/api/app/core/errors.py`: agrega mensajes seguros para los codigos canonicos.
- `database/migrations/0004_slice_03_ads_marketplace.up.sql`: usa `rate_bs_per_usd numeric(18,6)` y agrega lifetime counters a `credit_wallets`.
- `apps/web/src/app/page.tsx`: envia y muestra `rate_bs_per_usd`, e incluye `business_id` al crear anuncio.
- `apps/api/tests/test_ads_marketplace.py`: actualiza assertions y payloads al contrato canonico.

## Verificaciones ejecutadas

- `corepack pnpm --filter @nodo/web build`: OK.
- `python scripts\run_slice_00_tests.py`: 6 passed, 0 failed.
- `python scripts\run_slice_01_tests.py`: 6 passed, 0 failed.
- `python scripts\run_slice_02_tests.py`: OK.
- `python scripts\run_slice_03_tests.py`: OK.
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: 35 passed, 1 warning.
- `python -m ruff check apps\api scripts`: OK.
- `python -m compileall apps/api scripts`: OK.
- `rg -n "BOT_TOKEN|JWT_SECRET|JWT_REFRESH_SECRET|owner@example\.com|storage_path|account_value|BEGIN PRIVATE KEY|AKIA[0-9A-Z]{16}" apps\web\src apps\web\.next`: no matches.

## Riesgos residuales aceptados temporalmente

- Migraciones reales contra PostgreSQL/Supabase siguen pendientes hasta tener servicio/credenciales.
- Redis real sigue pendiente hasta tener servicio/credenciales.
- Storage privado real sigue pendiente por slice 02/hardening.
- Smoke manual dentro de Telegram real no ejecutado.
- Warning Starlette/httpx TestClient sigue presente y no bloquea este slice.
- No existe flujo real para comprar/acreditar creditos hasta `slice_08_credits_referrals`; negocios sin creditos seed/founder no pueden publicar, como exige el contrato.

## Estado

slice_03_ads_marketplace = OWNER_ACCEPTED_FOR_NEXT_SLICE

No se declara READY_FOR_REAL_USE.
No se avanza automaticamente a slice_04 sin prompt/report-first.
