# Architecture Review - Ads Postgres Repository Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica del repositorio Postgres de anuncios.

No se cambiaron reglas de anuncios, creditos, holds, ledger, endpoints, payloads, estados, frontend, contratos, migraciones ni servicios reales.

## Archivos modificados

- `apps/api/app/modules/ads/postgres_repository.py`
- `apps/api/app/modules/ads/repository.py`

## Cambio realizado

- `PostgresAdRepository` fue movido a `ads/postgres_repository.py`.
- `ads/repository.py` quedo como facade de compatibilidad.
- Los imports existentes desde `app.modules.ads.repository` siguen funcionando.
- `InMemoryAdRepository` sigue en `ads/memory_repository.py`.

## Medicion despues del corte

- `apps/api/app/modules/ads/repository.py`: 6 lineas
- `apps/api/app/modules/ads/postgres_repository.py`: 430 lineas
- `apps/api/app/modules/ads/memory_repository.py`: 303 lineas
- `apps/api/app/modules/ads/row_mappers.py`: 46 lineas

Antes de los cortes de ads, `ads/repository.py` tenia 726 lineas.

## Validacion ejecutada

- `python -m pytest apps\api\tests\test_ads_marketplace.py apps\api\tests\test_order_creation.py apps\api\tests\test_business_order_ops.py apps\api\tests\test_credits_referrals.py -q`: 37 passed, 1 warning
- `python -m ruff check apps\api\app\modules\ads apps\api\tests\test_ads_marketplace.py apps\api\tests\test_order_creation.py apps\api\tests\test_business_order_ops.py apps\api\tests\test_credits_referrals.py`: PASS
- `python -m pytest apps\api\tests -q`: 133 passed, 1 warning
- `python -m ruff check apps\api scripts`: PASS
- `python -m compileall apps\api scripts`: PASS
- `corepack pnpm --filter @nodo/web build`: PASS

## Riesgo residual

`PostgresAdRepository` sigue teniendo funciones con SQL de credit hold, release y consume. Ya no esta mezclado con memoria ni mappers, pero aun tiene operaciones financieras densas.

Siguiente corte recomendado:

1. medir `PostgresAdRepository.release_hold`
2. medir `PostgresAdRepository.consume_hold_for_order`
3. extraer helpers privados para ledger mapping y actualizaciones, manteniendo cada operacion en una sola transaccion
