# slice_28B_order_create_staging_profile - BUILDER_REPORT

Estado final: `READY_FOR_OWNER_REVIEW`

## Objetivo

Medir `POST /api/v1/orders` en staging con perfil por etapas, usando el runner cloud, para identificar si el siguiente cuello despues de 28A estaba en marketplace, en la ruta externa o en creacion de orden.

## Cambios construidos

- `apps/api/app/modules/orders/helpers.py`
  - Agrega un gate por request para permitir `_profile` de orden sin depender de `NODO_INTERNAL_PROFILING`.

- `apps/api/app/modules/orders/remitter_routes.py`
  - Activa `_profile` solo bajo el gate seguro de staging: `APP_ENV=staging`, `ENABLE_STAGING_PROFILING=1` y header `X-NODO-Profile: 1`.

- `scripts/cloud_load_runner.py`
  - Envia `X-NODO-Profile: 1` tambien en `POST /api/v1/orders` cuando `profile_marketplace=true`.

- `apps/api/tests/test_order_creation.py`
  - Cubre que el perfil de orden requiere staging + env flag + header.
  - Cubre que production no devuelve `_profile` aunque se mande el header.

- `apps/api/tests/test_staging_validation_tooling.py`
  - Cubre que el runner cloud agrega header de profiling a `order_create`.

## Deploy staging

- Build staging desplegado: `staging-28b-20260711192826`
- Railway deployment ID: `da75b10b-580c-49d5-a939-69645ad7d6e8`
- `/version`: `200`
- `/ready`: DB `ok`, Redis `ok`

No se desplego produccion real.

## Evidencia cloud

### c50

- GitHub Actions run: `29172604417`
- Requests: `200`
- Concurrency: `50`
- Resultado: `50x 201`, `150x 200`, errores `0`
- Perfiles capturados: `order_create=50`, `marketplace_read=150`
- `order_create` client p95: `987.4062ms`
- `order_create` backend p95: `571.6427ms`
- `marketplace_read` client p95: `625.7529ms`
- `marketplace_read` backend p95: `97.7111ms`

Top stages de orden c50:

- `auth:get_user_by_id` p95 `195.6837ms`
- `service:get_existing_idempotency` p95 `187.1105ms`
- `audit:order_created_and_ad_moved` p95 `163.7498ms`
- `transaction:create_order_and_move_ad` p95 `146.0914ms`
- `db_reads:order_create_context` p95 `107.1445ms`

### c100

- GitHub Actions run: `29172904002`
- Requests: `400`
- Concurrency: `100`
- Resultado: `100x 201`, `300x 200`, errores `0`
- Perfiles capturados: `order_create=100`, `marketplace_read=300`
- `order_create` client p95: `1734.9137ms`
- `order_create` backend p95: `977.2929ms`
- `marketplace_read` client p95: `2357.7119ms`
- `marketplace_read` backend p95: `172.2158ms`

Top stages de orden c100:

- `service:get_existing_idempotency` p95 `383.4777ms`
- `audit:order_created_and_ad_moved` p95 `362.3048ms`
- `auth:get_user_by_id` p95 `292.5302ms`
- `transaction:create_order_and_move_ad` p95 `182.4423ms`
- `db_reads:order_create_context` p95 `126.7351ms`

## Lectura tecnica

28A redujo el problema de cache/marketplace. 28B muestra que el siguiente limite medido esta en `POST /orders`.

La orden no falla funcionalmente, pero a c100 el backend de orden llega a p95 cercano a 1s. No es un unico punto gigante; son varias operaciones moderadas sumadas y amplificadas por concurrencia:

- consulta de usuario/auth,
- lookup de idempotencia existente,
- auditoria,
- transaccion de creacion y movimiento de anuncio,
- lecturas de contexto de orden.

## Cleanup

Cleanup ejecutado y verificado para:

- `gha_29172604417_1_mixed-read-order`
- `gha_mixed50_slice28b_retry_fixture_20260711193850`
- `gha_29172904002_1_mixed-read-order`
- `gha_mixed100_slice28b_retry_fixture_20260711194620`

Verificacion DB posterior: `0` businesses y `0` ads vivos por esos run IDs.

## Validaciones

- `pytest apps/api/tests/test_staging_validation_tooling.py -k "cloud_load_runner_order_create_adds_profile_header_when_enabled or cloud_load_runner_mixed_marketplace_profiles_are_captured"`: `2 passed`
- `pytest apps/api/tests/test_order_creation.py -k "profile"`: `3 passed`
- `pytest apps/api/tests/test_staging_validation_tooling.py -k "cloud_load_runner"`: `4 passed`
- `pytest apps/api/tests/test_order_creation.py apps/api/tests/test_staging_validation_tooling.py`: `69 passed`
- `python -m pytest apps/api/tests -q`: `257 passed`
- `python -m ruff check apps/api scripts`: OK
- `python -m compileall apps/api apps/web/src scripts`: OK
- `corepack pnpm --filter @nodo/web build`: OK

## Riesgos residuales

- El setup de fixtures staging es lento: c50 `283.774s`, c100 `566.7119s`. No afecta la medicion del runner cloud, pero si afecta costo/operacion de pruebas.
- `order_create` p95 backend en c100 sigue alto para una operacion frecuente.
- Los cambios backend de profiling son staging-gated, pero siguen siendo cambios de codigo de aplicacion y deben mantenerse fuera de exposicion production mediante env/header.
- No se declaro capacidad 10,000 usuarios.

## Confirmacion

- No se cambio infraestructura.
- No se subieron workers, pool, planes ni replicas.
- No se cambio DB schema.
- No se tocaron reglas de lifecycle, pagos, creditos, disputas ni bots.
- No se declaro `READY_FOR_REAL_USE`.
