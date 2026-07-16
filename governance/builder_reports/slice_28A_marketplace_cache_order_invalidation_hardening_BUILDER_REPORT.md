# slice_28A_marketplace_cache_order_invalidation_hardening

Estado final: READY_FOR_OWNER_REVIEW

## Objetivo

Reducir el recalentamiento repetido de `GET /api/v1/ads/search` cuando muchas órdenes toman anuncios en poco tiempo, sin permitir que el marketplace muestre anuncios ya reservados.

La evidencia cloud previa mostró que, en mixed c100, el backend seguía sano pero marketplace tenía presión por cache reheating:

- `cache:lock_wait p95`: ~475 ms
- `db:query:list_marketplace_ads_with_businesses p95`: ~90 ms
- `repo:list_marketplace_ads_with_businesses p95`: ~238 ms
- 100 órdenes concurrentes invalidaban marketplace repetidamente.

## Cambios realizados

- `apps/api/app/shared/cache.py`
  - Agrega markers temporales.
  - Agrega lectura batch de markers.
  - Agrega invalidación debounced para evitar version bumps repetidos durante una ventana corta.

- `apps/api/app/modules/ads/marketplace_cache.py`
  - Agrega marker `ad_unavailable:{ad_id}` con TTL igual al TTL de marketplace.
  - Agrega invalidación agrupada de órdenes con ventana de 2 segundos.

- `apps/api/app/modules/ads/marketplace.py`
  - Filtra respuestas cacheadas contra markers de anuncios no disponibles.
  - Si no puede verificar markers, no confía en la cache y cae a lectura fresca.

- `apps/api/app/modules/orders/create_order_flow.py`
  - Al crear orden, usa invalidación de marketplace específica para orden.

- `apps/api/app/modules/orders/service.py`
  - Inyecta la nueva invalidación específica para órdenes.

- `apps/api/app/modules/orders/service_support.py`
  - Implementa fallback seguro: si no puede marcar el anuncio como no disponible, ejecuta la invalidación fuerte anterior.

- `apps/api/tests/test_order_creation.py`
  - Agrega regresión que prueba dos órdenes consecutivas contra marketplace cache caliente:
    - La primera orden puede recalentar.
    - La segunda no debe recalentar de nuevo dentro de la ventana.
    - Ningún anuncio tomado aparece en marketplace.

## Qué no cambió

- No cambié lifecycle de órdenes.
- No cambié reglas de créditos.
- No cambié pagos.
- No cambié DB/migraciones.
- No cambié frontend.
- No cambié infraestructura.
- No hice deploy.
- No declaré `READY_FOR_REAL_USE`.

## Validaciones

- `python -m pytest apps\api\tests\test_order_creation.py::test_create_order_filters_reserved_ad_from_warm_marketplace_cache_without_second_reheat apps\api\tests\test_order_creation.py::test_create_order_invalidates_marketplace_cache_for_reserved_ad apps\api\tests\test_ads_marketplace.py::test_marketplace_search_uses_short_cache_and_ad_mutation_invalidates_it -q --tb=short`
  - `3 passed, 1 warning`

- `python -m pytest apps\api\tests\test_ads_marketplace.py apps\api\tests\test_order_creation.py -q --tb=short`
  - `36 passed, 1 warning`

- `python -m pytest apps\api\tests -q`
  - `254 passed, 1 warning`

- `python -m ruff check apps\api scripts`
  - `All checks passed!`

- `python -m compileall apps\api apps\web\src scripts`
  - OK

- `corepack pnpm --filter @nodo/web build`
  - OK

## Validación staging/cloud post-deploy

Deploy staging:

- Railway project: `nodo-api-staging`
- Service: `nodo-api`
- Deployment ID: `e9f57920-d004-42f5-aef4-49d5ccb5a0fd`
- Build: `staging-28a-20260711185548`
- `/version`, `/health`, `/ready`: OK

Cloud mixed c50:

- GitHub Actions run: `29171602101`
- Requests: `200`
- Concurrency: `50`
- Status: `50x 201`, `150x 200`
- Errors: `0`
- Total p95: `1180.9259ms`
- Marketplace read p95: client `235.3008ms`, backend `28.9403ms`
- Order create p95: client `1273.7763ms`, backend `703.1224ms`
- Marketplace cache:
  - `cache:lock_wait count`: `4`
  - `cache:lock_wait p95`: `9.9499ms`
  - marketplace DB query count: `1`
  - unavailable markers filtered cached marketplace responses: `149`

Cloud mixed c100:

- GitHub Actions run: `29171926212`
- Requests: `400`
- Concurrency: `100`
- Status: `100x 201`, `300x 200`
- Errors: `0`
- Total p95: `3135.1946ms`
- Marketplace read p95: client `3268.3649ms`, backend `180.267ms`
- Order create p95: client `1761.0368ms`, backend `1104.6346ms`
- Marketplace cache:
  - `cache:lock_wait count`: `32`
  - `cache:lock_wait p95`: `221.7376ms`
  - marketplace DB query count: `2`
  - unavailable markers filtered cached marketplace responses: `263`

Compared with the prior mixed c100 profile run, the cache-specific bottleneck improved:

- `cache:lock_wait p95`: about `475.4ms` -> `221.7376ms`
- marketplace DB query count: `10` -> `2`
- marketplace backend p95: about `451ms` -> `180.267ms`

But end-to-end p95 did not materially improve:

- mixed c100 total p95 stayed around `3s`.
- remaining latency is still dominated by external/client/edge path and order-create backend time, not marketplace DB query volume.

Cleanup:

- `gha_29171602101_1_mixed-read-order`: cleaned.
- `gha_mixed50_slice28a_fixture_20260711190056`: cleaned.
- `gha_29171926212_1_mixed-read-order`: cleaned.
- `gha_mixed100_slice28a_fixture_20260711190902`: cleaned.
- Post-cleanup verification: `0` businesses, `0` ads, `0` sessions for c50/c100 fixture run IDs.

Secret scan:

- Only `DATABASE_URL` and `REDIS_URL` appeared with value `[REDACTED]`.
- No real tokens, `storage_path`, `account_value`, signed URLs, private keys or seed phrases found in slice 28A evidence.

## Riesgos residuales

- Durante la ventana de 2 segundos, una lista cacheada puede mostrar menos anuncios hasta refrescarse, pero no debe mostrar anuncios ya tomados.
- Si la capa de markers falla, el código vuelve a la invalidación fuerte anterior.
- El p95 externo sigue alto en c100. Este slice redujo el recalentamiento del marketplace, pero no elimina el siguiente cuello: path externo/cliente/edge y latencia de order-create bajo mixed c100.
