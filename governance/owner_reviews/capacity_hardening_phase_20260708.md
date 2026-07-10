# Capacity Hardening Phase - 2026-07-08

## Estado

PARTIAL_HARDENING_COMPLETED

No se declara `READY_FOR_REAL_USE`.

Esta fase corrige una parte importante del problema detectado en `system_improvement_audit_20260708.md`: el stress ya no depende solamente del harness e2e secuencial que se quedaba atrapado creando/verificando negocios.

## Cambios realizados

### Nuevo harness separado

Archivo:

- `scripts/capacity_real.py`

Agrega un harness por escenarios:

- `marketplace-reads`
- `order-flow`
- `order-race`
- `all`

El harness crea un dataset interno preparado:

- negocios aprobados;
- `business_access_links` activos;
- payment methods aprobados;
- wallets con creditos;
- anuncios creados por el endpoint real `/api/v1/business/ads`.

Importante:

- No usa el self-onboarding legacy como centro de la prueba.
- No sube documentos ni pasa por submit verification para medir ordenes.
- Sigue usando endpoints reales para marketplace y ordenes.

### Validacion de schema endurecida

Archivo:

- `scripts/validate_local_schema.py`

Antes solo contaba tablas/indices y podia dar falso verde aunque faltaran columnas criticas.

Ahora valida tambien:

- `users.terms_accepted_at`
- `users.terms_version`
- columnas principales de `business_access_links`
- columnas principales de `business_intake_requests`
- tablas `business_access_links`
- tabla `business_intake_requests`

### Helpers de migracion puntual

Archivos:

- `scripts/apply_terms_migration.py`
- `scripts/apply_migration_file.py`

Se agregaron porque `scripts/apply_local_migrations.py` no pudo aplicar toda la cadena local: fallo en `0004` por constraint ya existente `ads_credit_hold_ledger_fk`.

Esto queda como deuda real:

- las migraciones antiguas no son totalmente idempotentes;
- el schema validator anterior no detectaba drift de columnas/tablas.

### Runner slice 11 actualizado

Archivo:

- `scripts/run_slice_11_tests.py`

Ahora incluye `scripts/capacity_real.py` como smoke obligatorio de capacidad:

- 2 negocios preparados;
- 8 anuncios;
- 8 remitters;
- 12 marketplace reads;
- 4 ordenes distintas;
- 5 requests compitiendo por el mismo anuncio;
- 5 replays concurrentes con la misma idempotency key.

## Hallazgos corregidos durante la fase

### Base local desfasada

El primer run fallo porque `users` no tenia:

- `terms_accepted_at`
- `terms_version`

Se aplico:

- `database/migrations/0012_terms_acceptance.up.sql`

Luego el schema validator endurecido detecto que tambien faltaban:

- `business_access_links`
- `business_intake_requests`

Se aplicaron:

- `0013_slice_14B1_business_access_links.up.sql`
- `0014_slice_14D_business_intake_bot.up.sql`
- `0015_audit_logs_business_intake_bot_actor.up.sql`

## Validacion final

### Runner slice 11

Archivo:

- `evidence/slice_runs/slice_11_hardening_deploy_test_results.json`

Resultado final:

- `test_hardening_local.py`: 8 passed
- infra local: OK
- schema validation: OK, 25 tablas, 142 indices, failures `[]`
- concurrency local: OK
- capacity harness nuevo: OK
- frontend build: OK
- ruff: OK
- compileall: OK
- frontend private/secret scan: OK, hits `[]`

### Capacity harness nuevo

Archivo:

- `evidence/slice_runs/slice_11_capacity_smoke.json`

Run:

- `slice11_capacity_smoke_1783554588`

Metricas:

- total requests: `26`
- invariant violations: todos `0`
- marketplace reads: `12/12` OK
- order creates distintas: `4/4` OK
- same-ad race: `1` orden creada, `4` conflictos `409` esperados, DB rows `1`
- duplicate idempotency race: `5` responses `201`, mismo order id, DB rows `1`
- negative balances: `0`
- double credit consumption: `0`

### Profile 25 local

Primer intento:

- run id: `capacity_profile25_20260708201301`
- negocios preparados: `25`
- anuncios preparados: `100`
- remitters preparados: `100`
- marketplace reads: `250/250` OK
- ordenes distintas: `100/100` OK
- resultado final: FAILED

Hallazgo:

- El producto no fue el primer problema detectado.
- El harness uso los `100` anuncios para ordenes distintas y luego intento usar anuncios ya tomados para `same_ad_race` e idempotencia.
- Eso produjo `404/409` en los escenarios reservados y dos invariant violations.
- Se corrigio `scripts/capacity_real.py` para reservar dos anuncios intactos para race/idempotency.

Segundo intento corregido:

- run id: `capacity_profile25_fixed_20260708201440`
- archivo: `evidence/slice_runs/capacity_profile25_fixed_20260708.json`
- negocios preparados: `25`
- anuncios preparados: `125`
- remitters preparados: `100`
- total requests: `385`
- invariant violations: todos `0`
- marketplace reads: `250/250` OK, p95 `2317.8899 ms`
- ordenes distintas: `100/100` OK, p95 `1088.7931 ms`
- same-ad race: `1` orden creada, `24` conflictos `409` esperados, DB rows `1`
- duplicate idempotency race: `10` responses `201`, mismo order id, DB rows `1`
- negative balances: `0`
- double credit consumption: `0`

Limpieza:

- `capacity_profile25_20260708201301`: ejecutada
- `capacity_profile25_fixed_20260708201440`: ejecutada
- negocios/anuncios/ordenes/ledger sinteticos removidos
- usuarios sinteticos y audit logs retenidos por diseno append-only

### Profile 25 con pagos y confirmaciones

Run:

- run id: `capacity_profile25_payments_20260708203724`
- archivo: `evidence/slice_runs/capacity_profile25_payments_20260708.json`

Dataset:

- negocios preparados: `25`
- anuncios marketplace: `125`
- anuncios para pagos/confirmaciones: `101`
- remitters preparados: `100`

Metricas:

- total requests medidos: `510`
- invariant violations: todos `0`
- marketplace reads: `250/250` OK
- ordenes distintas: `100/100` OK
- same-ad race: `1` orden creada, `24` conflictos `409` esperados, DB rows `1`
- duplicate idempotency race: `10` responses `201`, mismo order id, DB rows `1`
- payment reports setup: `0` errores
- confirmaciones distintas: `100/100` OK
- confirmaciones distintas DB state:
  - confirmed orders: `100`
  - archived ads: `100`
  - consume ledger rows: `100`
- same-order confirm race: `1` confirmacion exitosa, `24` conflictos `409` esperados
- same-order consume rows: `1`
- negative balances: `0`
- double credit consumption: `0`

Hallazgo adicional:

- El contrato/migracion actual usa `business_payment_methods.network = trc20` en minuscula para metodos USDT.
- `payment_reports.network` exige `TRC20` en mayuscula.
- El harness fue ajustado para respetar ambas reglas.
- Esto no bloquea la prueba, pero conviene documentarlo como inconsistencia semantica menor a limpiar en contratos/migraciones futuras.

Runner slice 11 actualizado:

- `scripts/run_slice_11_tests.py` ahora incluye `--payment-confirms 4` dentro del capacity smoke obligatorio.
- ultimo run integrado: `slice11_capacity_smoke_1783557535`
- invariant violations: todos `0`
- frontend build: OK
- ruff: OK
- compileall: OK
- frontend scan: OK
- pytest acumulado despues del cambio: `129 passed`, `1 warning`

### Pytest acumulado

Comando correcto:

```txt
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
```

Resultado:

- `129 passed`
- `1 warning` Starlette/httpx heredado

Nota:

- El primer intento sin `PYTHONPATH` fallo con `ModuleNotFoundError: No module named 'app'`.
- Eso fue error de invocacion, no fallo de producto.

## Limpieza

Se ejecutaron limpiezas de entidades operativas sinteticas para:

- `capacity_smoke_20260708`
- `capacity_smoke2_20260708`
- `capacity_smoke3_20260708`
- `capacity_smoke4_20260708`
- `capacity_profile25_20260708201301`
- `capacity_profile25_fixed_20260708201440`
- `capacity_payment_confirm_smoke2_20260708`
- `capacity_profile25_payments_20260708203724`
- `slice11_capacity_smoke`
- `slice11_capacity_smoke_1783554588`
- `slice11_capacity_smoke_1783557535`
- `concurrency1783554586`
- `concurrency1783557532`

Los usuarios sinteticos y audit logs quedan retenidos por diseno append-only.

## Riesgos que siguen abiertos

## Profile 50 local con payment-confirm

### Primer intento

Run:

```txt
capacity_profile50_payments_20260708210232
```

Escenario:

- negocios: `50`
- anuncios marketplace: `250`
- anuncios preparados para pago: `201`
- remitentes: `200`
- marketplace reads: `500`
- ordenes distintas: `200`
- same-ad race: `50`
- confirmaciones de pago distintas: `200`

Resultado importante:

- invariantes de base: `0` violaciones
- confirmaciones distintas: `200/200`
- credito consumido: `200` ledger rows
- anuncios archivados tras confirmacion: `200`
- same-order confirm race: `1` exito, `24` conflictos `409`, consume rows `1`

Bug detectado:

- same-ad race devolvio `1` success, `38` conflictos `409` y `11` respuestas `404`.
- El estado final de base quedo correcto, pero el error era semanticamente inestable.
- Bajo carrera, un anuncio ya tomado debe responder `AD_NOT_AVAILABLE` con `409`, no degradar a `404`.

### Fix aplicado

Archivos modificados:

- `apps/api/app/modules/orders/service.py`
- `apps/api/tests/test_order_creation.py`
- `scripts/capacity_real.py`

Cambios:

- `create_order` ahora devuelve `AD_NOT_AVAILABLE` con `409` cuando el anuncio existe pero ya no esta `active`.
- La prueba unitaria de anuncio pausado fue alineada a `409`.
- El harness de capacidad ahora cuenta `same_ad_unexpected_status` si el race devuelve algo distinto de `201` o `409`.

Validacion del fix:

- `python -m pytest apps\api\tests\test_order_creation.py -q`: `9 passed`, `1 warning`
- `python scripts\run_slice_11_tests.py`: OK
- `python -m pytest apps\api\tests -q`: `129 passed`, `1 warning`
- `python -m compileall apps scripts`: OK

### Revalidacion Profile 50 corregido

Run:

```txt
capacity_profile50_payments_fix_20260708210814
```

Evidencia:

```txt
evidence/slice_runs/capacity_profile50_payments_fix_20260708.json
evidence/slice_runs/cleanup_execute_capacity_profile50_payments_fix_20260708210814.json
```

Metricas:

- total requests: `985`
- total errors: `73`
- error rate: `0.0741`
- duration: `103.98s`
- throughput: `9.4729 req/s`
- p50: `4056.8211ms`
- p95: `4177.0262ms`
- p99: `4188.6974ms`

Notas sobre errores:

- Los `73` errores son rechazos esperados de carrera/idempotencia, no fallos de producto.
- same-ad race: `1` orden creada, `49` conflictos `409`, `0` estados inesperados.
- same-order confirm race: `1` confirmacion exitosa, `24` conflictos `409`.

Estado de pagos/creditos:

- confirmaciones distintas: `200/200`
- ordenes confirmadas: `200`
- anuncios archivados: `200`
- ledger consume rows: `200`
- same-order race consume rows: `1`

Invariant violations:

- `marketplace_read_errors`: `0`
- `order_create_errors`: `0`
- `same_ad_success_count_invalid`: `0`
- `same_ad_unexpected_status`: `0`
- `same_ad_db_rows_invalid`: `0`
- `duplicate_idempotency_response_mismatch`: `0`
- `duplicate_idempotency_db_rows_invalid`: `0`
- `payment_report_setup_errors`: `0`
- `confirm_distinct_errors`: `0`
- `confirm_distinct_state_invalid`: `0`
- `confirm_same_order_success_count_invalid`: `0`
- `confirm_same_order_double_consume`: `0`
- `negative_balances`: `0`
- `double_credit_consumption`: `0`
- `db_errors`: `0`

Limpieza:

- Se ejecuto cleanup para `capacity_profile50_payments_20260708210232`.
- Se ejecuto cleanup para `capacity_profile50_payments_fix_20260708210814`.
- Se limpiaron tambien `concurrency1783559223` y `slice11_capacity_smoke_1783559226`.
- Usuarios sinteticos y audit logs quedan retenidos por diseno append-only.

Schema post-limpieza:

- tablas: `25`
- indices: `142`
- Redis ping: OK
- failures: `[]`

## Profile 100 local con payment-confirm

Run:

```txt
capacity_profile100_payments_20260708213207
```

Evidencia:

```txt
evidence/slice_runs/capacity_profile100_payments_20260708.json
evidence/slice_runs/cleanup_execute_capacity_profile100_payments_20260708213207.json
```

Escenario:

- negocios: `100`
- anuncios por negocio: `5`
- anuncios marketplace preparados: `500`
- anuncios preparados para pagos: `401`
- remitentes: `400`
- marketplace reads: `1000`
- ordenes distintas: `400`
- same-ad race: `100`
- confirmaciones de pago distintas: `400`

Metricas globales:

- total requests: `1935`
- total errors: `123`
- error rate: `0.0636`
- duration: `199.536s`
- throughput: `9.6975 req/s`
- p50: `7875.6601ms`
- p95: `8043.2967ms`
- p99: `8054.4557ms`

Notas sobre errores:

- Los `123` errores son rechazos esperados por carreras controladas.
- same-ad race: `1` orden creada, `99` conflictos `409`, `0` estados inesperados.
- same-order confirm race: `1` confirmacion exitosa, `24` conflictos `409`.

Estado de pagos/creditos:

- confirmaciones distintas: `400/400`
- ordenes confirmadas: `400`
- anuncios archivados: `400`
- ledger consume rows: `400`
- same-order race consume rows: `1`

Invariant violations:

- `marketplace_read_errors`: `0`
- `order_create_errors`: `0`
- `same_ad_success_count_invalid`: `0`
- `same_ad_unexpected_status`: `0`
- `same_ad_db_rows_invalid`: `0`
- `duplicate_idempotency_response_mismatch`: `0`
- `duplicate_idempotency_db_rows_invalid`: `0`
- `payment_report_setup_errors`: `0`
- `confirm_distinct_errors`: `0`
- `confirm_distinct_state_invalid`: `0`
- `confirm_same_order_success_count_invalid`: `0`
- `confirm_same_order_double_consume`: `0`
- `negative_balances`: `0`
- `double_credit_consumption`: `0`
- `db_errors`: `0`

Limpieza:

- Se ejecuto cleanup para `capacity_profile100_payments_20260708213207`.
- Se eliminaron entidades operativas sinteticas: `100` businesses, `901` ads, `803` orders, `401` payment reports, `1302` credits ledger rows, `1605` order state events y `501` sessions.
- Usuarios sinteticos y audit logs quedan retenidos por diseno append-only.

Schema post-limpieza:

- tablas: `25`
- indices: `142`
- Redis ping: OK
- failures: `[]`

Pytest acumulado post-run:

- `129 passed`
- `1 warning` Starlette/httpx heredado

### Observacion de rendimiento

El profile 50 corrigio consistencia, y profile 100 confirma que las invariantes aguantan. El problema abierto ahora es performance:

- profile 50 marketplace p95: `4181.6205ms`
- profile 50 create order p95: `2039.0981ms`
- profile 50 confirm payment p95: `2127.6777ms`
- profile 100 marketplace p95: `8049.2031ms`
- profile 100 create order p95: `3498.8291ms`
- profile 100 confirm payment p95: `4011.9091ms`

Esto no rompe invariantes, pero si marca trabajo pendiente de performance antes de uso real. No recomiendo subir a 200/1000 sin perf profiling y optimizacion de consultas/rutas calientes.

### No prueba aun 200-1000 clientes

El nuevo harness demuestra que ya podemos aislar escenarios y profile 100 paso incluyendo confirmaciones de pago, pero aun no ejecutamos cargas mayores.

Pendiente:

- 200 negocios preparados;
- 500-1000 marketplace reads;
- 200-500 ordenes;
- carreras masivas sobre anuncios;
- payment-report/confirm-payment concurrente en profile 50/100 y en servicios reales;
- job dry-run durante estados mixtos.

### Migraciones antiguas no son idempotentes

`scripts/apply_local_migrations.py` fallo en `0004` por constraint duplicado.

Pendiente:

- hacer idempotentes constraints viejos;
- o crear un migration runner con tracking real de migraciones aplicadas.

### Stress real cloud sigue pendiente

Esta fase valido local Docker/ASGI con Postgres/Redis local.

Pendiente:

- repetir estos escenarios contra Supabase/Redis cloud;
- medir latencia real;
- limpiar post-run;
- emitir `REAL_SERVICES_CAPACITY_REPORT.md`.

## Follow-up: marketplace/pool hardening

Despues del profile 100 se hizo una ronda adicional de reparacion de capacidad sobre dos puntos calientes:

1. Marketplace search hacia dos consultas separadas.
2. Conexiones PostgreSQL sin pool global acotado.

### Reparaciones aplicadas

- `apps/api/app/modules/ads/service.py`: marketplace search ahora usa una ruta optimizada del repository si existe.
- `apps/api/app/modules/ads/repository.py`: agregado `list_marketplace_ads_for_marketplace`, con join directo `ads + businesses` para filtrar anuncios activos de negocios aprobados sin cargar primero todos los business ids elegibles.
- `apps/api/app/shared/db/connection.py`: `pooled_connect` ahora usa un pool global acotado por `DATABASE_URL`, con reuso por thread/contexto anidado.
- `.env.example`, `.env.local.example`, `.env.staging.example` y `control_plane/11_OPERATIONS/ENVIRONMENT_VARIABLES.md`: agregadas `NODO_DB_POOL_MAX_SIZE` y `NODO_DB_POOL_TIMEOUT_SECONDS`.

### Fallo real detectado y corregido

Primer run optimizado, antes del pool acotado:

- run prefix: `capacity_profile50_marketplace_opt`
- resultado: fallo por PostgreSQL `too many clients`
- causa: el "pool" anterior era thread-local y podia crear demasiadas conexiones bajo rafaga ASGI/TestClient.
- cleanup parcial: `cleanup_execute_capacity_profile50_marketplace_opt_partial.json`
- cleanup exit code: `0`
- schema post-cleanup: `25` tablas, `142` indices, Redis ping OK.

### Revalidacion con pool default 20

Run: `capacity_profile50_pool_opt_20260708215459`

- total requests: `985`
- total errors: `73`
- errors esperados: carreras controladas `409`
- invariant violations: todas `0`
- duration: `52.703s`
- throughput: `18.6897 req/s`
- p50: `5766.4702ms`
- p95: `5834.3742ms`
- marketplace p95: `5843.7244ms`
- create order p95: `2296.3722ms`
- confirm payment p95: `1895.5982ms`
- cleanup: `cleanup_execute_capacity_profile50_pool_opt_20260708215459.json`, exit code `0`

Conclusion: corrige el fallo de conexiones, pero genera cola visible bajo 500 marketplace reads simultaneos.

### Revalidacion con pool 50

Run: `capacity_profile50_pool50_opt_20260708215635`

- total requests: `985`
- total errors: `73`
- errors esperados: carreras controladas `409`
- invariant violations: todas `0`
- duration: `49.938s`
- throughput: `19.7244 req/s`
- p50: `3064.5599ms`
- p95: `3107.3111ms`
- marketplace p95: `3109.4373ms`
- create order p95: `2082.8248ms`
- confirm payment p95: `2096.0349ms`
- cleanup: `cleanup_execute_capacity_profile50_pool50_opt_20260708215635.json`, exit code `0`

Conclusion: mejor configuracion observada en local para este profile. Baja mucho la cola del marketplace sin romper DB ni invariantes.

### Revalidacion con pool 80

Run: `capacity_profile50_pool80_opt_20260708215801`

- total requests: `985`
- total errors: `73`
- errors esperados: carreras controladas `409`
- invariant violations: todas `0`
- duration: `52.38s`
- throughput: `18.805 req/s`
- p50: `4276.1702ms`
- p95: `4486.7485ms`
- marketplace p95: `4492.5292ms`
- create order p95: `2052.1507ms`
- confirm payment p95: `1729.7973ms`
- cleanup: `cleanup_execute_capacity_profile50_pool80_opt_20260708215801.json`, exit code `0`

Conclusion: mas conexiones no fue mejor en esta maquina. Pool 80 mantiene consistencia, pero empeora marketplace p95 frente a pool 50.

### Estado despues de hardening

Mejora concreta:

- Se elimino el fallo `too many clients`.
- La carrera same-ad queda en `1` creacion y el resto `409`, sin `404` ni estados inesperados.
- La carrera same-order confirm queda en `1` consumo de creditos, sin doble consumo.
- Pool 50 queda como recomendacion local/staging inicial, sujeto a validar contra Supabase/Redis cloud reales.

Riesgo que sigue abierto:

- Marketplace p95 local bajo 500 lecturas simultaneas sigue sobre `3s` incluso con pool 50.
- Antes de afirmar escala 200-1000, falta perf real con servidor ASGI desplegado y DB cloud/pooler, y posiblemente cache/read model para marketplace.

## Decision

Se avanzo en la direccion correcta: ahora tenemos una prueba separada para marketplace/ordenes/carreras sin depender del onboarding legacy.

Pero NODO sigue:

```txt
NOT_READY_FOR_REAL_USE
```

Siguiente paso recomendado:

1. correr regresion completa post-hardening;
2. repetir profile 50/100 contra servicios reales Supabase/Redis cloud;
3. agregar job dry-run durante estados mixtos;
4. evaluar cache/read model de marketplace si cloud mantiene p95 alto.
