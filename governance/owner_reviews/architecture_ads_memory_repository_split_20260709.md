# Architecture Review - Ads Memory Repository Split

Status: PASSED_AFTER_REFACTOR

## Scope

Separacion quirurgica del repositorio en memoria de anuncios.

No se cambiaron reglas de anuncios, creditos, holds, ledger, endpoints, payloads, estados, frontend, contratos, migraciones ni servicios reales.

## Archivos modificados

- `apps/api/app/modules/ads/memory_repository.py`
- `apps/api/app/modules/ads/repository.py`

## Cambio realizado

- `InMemoryAdRepository` fue movido a `ads/memory_repository.py`.
- `ads/repository.py` conserva `PostgresAdRepository`.
- `ads/repository.py` reexporta `InMemoryAdRepository` via `__all__` para mantener compatibilidad con imports existentes, incluyendo `app.main`.

## Medicion despues del corte

- `apps/api/app/modules/ads/repository.py`: 434 lineas
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

`ads/repository.py` todavia contiene `PostgresAdRepository` con operaciones de credit hold, release y consume.

Siguiente corte recomendado:

1. mover `PostgresAdRepository` a `ads/postgres_repository.py`
2. dejar `ads/repository.py` como facade
3. despues medir si `release_hold` y `consume_hold_for_order` necesitan helpers privados
