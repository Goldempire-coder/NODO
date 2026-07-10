# real_services_concurrency_2026_07_06

Estado: REAL_SERVICES_CONCURRENCY_PASSED

Fecha: 2026-07-06

## Alcance

Pruebas ejecutadas desde entorno local contra servicios reales de staging:

- Supabase PostgreSQL real.
- Upstash Redis real.
- Supabase Storage real para preparacion de negocio.
- FastAPI via `TestClient` local.

No se hizo deploy.
No se probo Railway.
No se probo Cloudflare Pages.
No se probo Telegram real.
No se declaro `READY_FOR_REAL_USE`.

## Observacion del owner

El stress profile 10 anterior era mayormente secuencial en creacion de ordenes. Eso no validaba suficientemente carreras simultaneas reales.

Riesgos que habia que probar:

- Dos o mas usuarios intentando tomar el mismo anuncio al mismo tiempo.
- Reintentos simultaneos con la misma `Idempotency-Key`.
- Ordenes simultaneas sobre anuncios distintos.
- Busquedas concurrentes de marketplace.
- Balances negativos o doble movimiento de creditos.
- Errores de DB/Redis bajo concurrencia.

## Cambio al harness

Archivo modificado:

```txt
scripts/concurrency_local.py
```

Cambios:

- Agregado `--same-ad-requests`.
- Agregada carrera de varios usuarios contra el mismo anuncio con distintas `Idempotency-Key`.
- Criterio esperado: exactamente una orden gana; las demas fallan de forma segura.
- Validacion DB: solo una fila de `orders` puede quedar asociada al anuncio disputado.
- IDs sinteticos ahora derivan de `run_id` para evitar colisiones entre corridas reales.
- El harness bloquea `unique_orders > 18` para un solo negocio MVP porque el rango maximo permitido es `$2,000`.

Validacion local del harness:

```txt
python scripts\concurrency_local.py --env-file .env.local.example --searches 10 --duplicate-requests 5 --same-ad-requests 5 --unique-orders 5 --run-id concurrency_harness_same_ad_local --output evidence\slice_runs\concurrency_harness_same_ad_local.json
```

Resultado:

```txt
exit_code: 0
same_ad_status_codes: 1 x 201, 4 x 409
same_ad_multiple_orders: 0
same_ad_success_count_invalid: 0
same_ad_db_rows_invalid: 0
negative_balances: 0
```

## Run 1 - Smoke concurrente real

Comando:

```txt
python scripts\concurrency_local.py --env-file .local\staging_real_services_smoke_LOCAL_ONLY.env --searches 50 --duplicate-requests 15 --same-ad-requests 25 --unique-orders 18 --run-id real_concurrency_smoke_valid_20260706034652 --output evidence\slice_runs\real_services_concurrency_smoke_valid_20260706.json
```

Resultado:

```txt
total_requests: 108
total_errors: 24
total_error_rate: 0.2222
duration_seconds: 283.032
p50_ms: 12055.5104
p95_ms: 20282.3102
p99_ms: 20412.8656
exit_code: 0
```

Detalle importante:

```txt
concurrent:ads:search
count: 50
status: 50 x 200
error_count: 0

concurrent:orders:duplicate_key
count: 15
status: 15 x 201
all returned same order id
error_count: 0

concurrent:orders:same_ad_different_keys
count: 25
status: 1 x 201, 22 x 409, 2 x 404
expected safe rejection: yes

concurrent:orders:create_unique
count: 18
status: 18 x 201
error_count: 0
```

Invariant violations:

```txt
duplicate_order_rows: 0
duplicate_order_response_mismatch: 0
duplicate_order_errors: 0
same_ad_multiple_orders: 0
same_ad_success_count_invalid: 0
same_ad_db_rows_invalid: 0
unique_order_errors: 0
search_errors: 0
negative_balances: 0
db_errors: 0
```

Evidencia:

```txt
evidence/slice_runs/real_services_concurrency_smoke_valid_20260706.json
evidence/slice_runs/real_services_concurrency_smoke_valid_20260706.log
evidence/slice_runs/real_services_concurrency_smoke_valid_post_schema_20260706.json
```

Post-schema:

```txt
table_count: 23
index_count: 128
redis_ping: True
failures: []
exit_code: 0
```

## Run 2 - Concurrencia dura real

Comando:

```txt
python scripts\concurrency_local.py --env-file .local\staging_real_services_smoke_LOCAL_ONLY.env --searches 200 --duplicate-requests 50 --same-ad-requests 100 --unique-orders 18 --run-id real_concurrency_hard_20260706035206 --output evidence\slice_runs\real_services_concurrency_hard_20260706.json
```

Resultado:

```txt
total_requests: 368
total_errors: 99
total_error_rate: 0.269
duration_seconds: 567.024
throughput_per_second: 0.649
p50_ms: 81614.8242
p95_ms: 82188.4662
p99_ms: 82541.0531
exit_code: 0
```

Detalle importante:

```txt
concurrent:ads:search
count: 200
status: 200 x 200
error_count: 0

concurrent:orders:duplicate_key
count: 50
status: 50 x 201
all returned same order id
error_count: 0

concurrent:orders:same_ad_different_keys
count: 100
status: 1 x 201, 39 x 409, 60 x 404
expected safe rejection: yes

concurrent:orders:create_unique
count: 18
status: 18 x 201
error_count: 0
```

Invariant violations:

```txt
duplicate_order_rows: 0
duplicate_order_response_mismatch: 0
duplicate_order_errors: 0
same_ad_multiple_orders: 0
same_ad_success_count_invalid: 0
same_ad_db_rows_invalid: 0
unique_order_errors: 0
search_errors: 0
negative_balances: 0
db_errors: 0
```

Evidencia:

```txt
evidence/slice_runs/real_services_concurrency_hard_20260706.json
evidence/slice_runs/real_services_concurrency_hard_20260706.log
evidence/slice_runs/real_services_concurrency_hard_post_schema_20260706.json
```

Post-schema:

```txt
table_count: 23
index_count: 128
redis_ping: True
failures: []
exit_code: 0
```

## Secret/private scan

Artefactos escaneados:

```txt
evidence/slice_runs/real_services_concurrency_smoke_valid_20260706.json
evidence/slice_runs/real_services_concurrency_smoke_valid_20260706.log
evidence/slice_runs/real_services_concurrency_hard_20260706.json
evidence/slice_runs/real_services_concurrency_hard_20260706.log
```

Patrones:

```txt
JWT_SECRET
JWT_REFRESH_SECRET
BOT_TOKEN
SUPABASE_SERVICE_ROLE_KEY
STRIPE_SECRET
storage_path
payment_instructions_snapshot
account_value
Traceback
DuplicatePreparedStatement
UniqueViolation
ORDER_EXPIRED
RATE_LIMITED
SESSION_EXPIRED
HTTP/1.1 5xx
```

Resultado:

```txt
forbidden_hits: 0
```

## Decision recomendada

```txt
REAL_SERVICES_CONCURRENCY_SAME_AD_READY
REAL_SERVICES_CONCURRENCY_IDEMPOTENCY_READY
REAL_SERVICES_CONCURRENCY_SEARCH_READY
NOT_READY_FOR_REAL_USE
```

## Interpretacion

La preocupacion del owner era valida: el profile10 secuencial no bastaba para afirmar seguridad bajo ordenes simultaneas.

Con el nuevo gate concurrente:

- 100 intentos simultaneos contra el mismo anuncio dejaron solo 1 orden real.
- 50 replays simultaneos con la misma `Idempotency-Key` devolvieron el mismo `order.id`.
- 18 ordenes simultaneas sobre anuncios distintos fueron creadas correctamente.
- 200 busquedas simultaneas respondieron 200 OK.
- No hubo balances negativos.
- No hubo doble fila para el anuncio disputado.
- No hubo errores DB/Redis ni leaks de secretos en evidencia.

## Riesgos residuales

- Esto prueba concurrencia local contra servicios reales usando `TestClient`, no trafico HTTP real desde deploy.
- No se ha probado aun Railway backend staging.
- No se ha probado aun Cloudflare Pages frontend staging.
- No se ha probado aun Telegram real.
- No se ha probado aun carga distribuida externa.
- La latencia fue alta en staging real, especialmente en busquedas concurrentes: p95 aproximado 82s en el run duro. Esto exige medicion desde deploy real, pooling y posible optimizacion antes de piloto amplio.

## Siguiente paso recomendado

Avanzar a deploy staging gobernado, pero incluir este gate como obligatorio despues del deploy:

1. Railway backend con variables reales de staging.
2. Migraciones/ready check desde Railway.
3. Cloudflare Pages frontend apuntando al backend staging.
4. Repetir smoke real.
5. Repetir concurrencia `same_ad` desde entorno deployado.
6. Solo despues evaluar `READY_FOR_PILOT`.
