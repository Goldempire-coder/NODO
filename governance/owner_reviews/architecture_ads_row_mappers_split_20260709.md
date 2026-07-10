# Architecture Review - Ads Row Mappers Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica de mappers de filas en el modulo de anuncios.

No se cambiaron reglas de anuncios, creditos, holds, ledger, endpoints, payloads, estados, frontend, contratos, migraciones ni servicios reales.

## Archivos modificados

- `apps/api/app/modules/ads/row_mappers.py`
- `apps/api/app/modules/ads/repository.py`

## Cambio realizado

- `ad_from_row` vive ahora en `ads/row_mappers.py`.
- `wallet_from_row` vive ahora en `ads/row_mappers.py`.
- `ads/repository.py` ya no contiene conversion manual de filas para anuncios y wallets.
- Las queries y operaciones de creditos/anuncios quedaron intactas.

## Medicion despues del corte

- `apps/api/app/modules/ads/repository.py`: 727 lineas
- `apps/api/app/modules/ads/row_mappers.py`: 46 lineas
- `InMemoryAdRepository` empieza en linea 13.
- `PostgresAdRepository` empieza en linea 308.

## Validacion ejecutada

- `python -m ruff check apps\api\app\modules\ads apps\api\tests\test_ads_marketplace.py apps\api\tests\test_order_creation.py apps\api\tests\test_business_order_ops.py apps\api\tests\test_credits_referrals.py`: PASS
- `python -m pytest apps\api\tests\test_ads_marketplace.py apps\api\tests\test_order_creation.py apps\api\tests\test_business_order_ops.py apps\api\tests\test_credits_referrals.py -q`: 37 passed, 1 warning
- `python -m pytest apps\api\tests -q`: 133 passed, 1 warning
- `python -m ruff check apps\api scripts`: PASS
- `python -m compileall apps\api scripts`: PASS
- `corepack pnpm --filter @nodo/web build`: PASS

## Riesgo residual

`ads/repository.py` todavia mezcla repositorio en memoria y repositorio Postgres. Tambien conserva operaciones de credit hold y ledger en el mismo archivo.

Siguiente corte recomendado:

1. mover `InMemoryAdRepository` a `ads/memory_repository.py`
2. dejar `ads/repository.py` como facade temporal o conservar solo Postgres, segun riesgo
3. validar anuncios, ordenes y creditos antes de tocar cualquier logica de ledger
