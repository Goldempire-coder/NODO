# real_services_smoke_stress_2026_07_05

Estado: REAL_SERVICES_PROFILE10_PASSED_AFTER_FIXES

Fecha: 2026-07-05

## Alcance

Pruebas ejecutadas desde entorno local contra servicios reales de staging:

- Supabase PostgreSQL real.
- Upstash Redis real.
- Supabase Storage real.
- FastAPI via `TestClient` local.

No se hizo deploy.
No se probo Railway.
No se probo Cloudflare Pages.
No se probo Telegram real.
No se declaro `READY_FOR_REAL_USE`.

## Env usado

Archivo local ignorado por Git:

```txt
.local/staging_real_services_smoke_LOCAL_ONLY.env
```

El archivo combina variables reales de DB/Redis/Storage con secretos sinteticos para `BOT_TOKEN`, JWT y Stripe en modo local.

## Correcciones hechas durante la verificacion

### 1. Supabase pooler / PgBouncer

El primer stress largo contra Supabase real expuso:

```txt
psycopg.errors.DuplicatePreparedStatement: prepared statement "_pg3_0" already exists
```

Correccion:

- Se agrego `connect(database_url, **kwargs)` en `apps/api/app/shared/db/connection.py`.
- Ese wrapper usa `prepare_threshold=None`.
- Runtime DB pool, health checks y scripts de schema/stress usan ahora el wrapper central.

Validacion:

```txt
python -m ruff check apps\api scripts
python -m compileall apps\api scripts
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_hardening_local.py -q
```

Resultado:

```txt
ruff: OK
compileall: OK
test_hardening_local.py: 8 passed
```

### 2. Harness de stress real

El profile 10 secuencial original podia dejar expirar ordenes porque creaba muchos negocios/anuncios/ordenes antes de reportar pagos.

Correccion:

- `scripts/stress_local.py` ahora soporta `--workflow-mode interleaved`.
- En modo `interleaved`, completa flujos de orden dentro del deadline.
- `scripts/local_smoke.py` y `scripts/stress_local.py` usan Telegram IDs sinteticos derivados de `run_id`, evitando colisiones entre runs reales.

Validacion local de harness:

```txt
python scripts\stress_local.py --env-file .env.local.example --profile initial --cap-businesses 1 --cap-orders 2 --workflow-mode interleaved --run-id harness_unique_ids_smoke --output evidence\slice_runs\stress_harness_unique_ids_smoke.json
```

Resultado:

```txt
exit_code: 0
```

## Gate 1 - Schema/Redis real inicial

Comando:

```txt
python scripts\validate_local_schema.py --env-file .local\staging_real_services_smoke_LOCAL_ONLY.env --output evidence\slice_runs\real_services_schema_validation_20260705.json
```

Resultado:

```txt
table_count: 23
index_count: 128
redis_ping: True
failures: []
exit_code: 0
```

Evidencia:

```txt
evidence/slice_runs/real_services_schema_validation_20260705.json
```

## Gate 2 - Smoke funcional duro real

Comando:

```txt
python scripts\local_smoke.py --env-file .local\staging_real_services_smoke_LOCAL_ONLY.env --run-id real_smoke_20260705193524 --output evidence\slice_runs\real_services_smoke_20260705.json
```

Resultado:

```txt
run_id: real_smoke_20260705193524
total_requests: 28
total_errors: 0
total_error_rate: 0.0
duration_seconds: 110.25
p95_ms: 6825.6655
forbidden_response_hits: []
exit_code: 0
```

Flujos cubiertos:

- health/ready/version
- Telegram auth sintetico
- negocio creado
- 4 documentos privados subidos a Supabase Storage real
- verificacion enviada
- admin aprueba negocio
- admin ajusta creditos
- anuncio creado
- busqueda marketplace
- orden creada
- instrucciones de pago reveladas
- evidencia de pago subida a Supabase Storage real
- reporte de pago
- negocio confirma pago
- negocio marca entregado
- mensaje de chat
- disputa abierta
- admin resuelve disputa con `keep_under_review`
- job dry-run
- admin dashboard
- admin metrics

Evidencia:

```txt
evidence/slice_runs/real_services_smoke_20260705.json
```

## Gate 3 - Stress real controlado cap5x25

Comando:

```txt
python scripts\stress_local.py --env-file .local\staging_real_services_smoke_LOCAL_ONLY.env --profile 10 --cap-businesses 5 --cap-orders 25 --run-id real_stress10_cap5x25_20260705205239 --output evidence\slice_runs\real_services_stress_profile10_cap5x25_20260705.json
```

Resultado:

```txt
profile: 10
target.businesses: 5
target.orders: 25
actual.businesses: 5
actual.ads: 25
actual.orders: 25
actual.workflow_orders: 5
total_requests: 143
total_errors: 0
total_error_rate: 0.0
duration_seconds: 759.862
throughput_per_second: 0.1882
p50_ms: 4677.0097
p95_ms: 7586.0413
p99_ms: 10313.4233
exit_code: 0
```

Invariant violations:

```txt
idempotency_duplicates: 0
idempotency_replay_conflicts: 0
double_credit_consumption: 0
double_credit_accreditation: 0
negative_balances: 0
invalid_transitions: 0
redis_failures: 0
db_errors: 0
timeouts: 0
deadlocks: 0
job_lock_failures: 0
```

Evidencia:

```txt
evidence/slice_runs/real_services_stress_profile10_cap5x25_20260705.json
evidence/slice_runs/real_services_stress_profile10_cap5x25_20260705.log
```

## Gate 4 - Pooler fix smoke real

Comando:

```txt
python scripts\stress_local.py --env-file .local\staging_real_services_smoke_LOCAL_ONLY.env --profile 10 --cap-businesses 2 --cap-orders 5 --workflow-mode interleaved --run-id real_pooler_fix_smoke_20260705 --output evidence\slice_runs\real_services_pooler_fix_smoke_20260705.json
```

Resultado:

```txt
workflow_mode: interleaved
actual.businesses: 2
actual.ads: 5
actual.orders: 5
actual.workflow_orders: 2
total_requests: 44
total_errors: 0
total_error_rate: 0.0
p95_ms: 6377.6646
exit_code: 0
```

Post-schema:

```txt
table_count: 23
index_count: 128
redis_ping: True
failures: []
exit_code: 0
```

Evidencia:

```txt
evidence/slice_runs/real_services_pooler_fix_smoke_20260705.json
evidence/slice_runs/real_services_pooler_fix_post_schema_20260705.json
```

## Gate 5 - Stress real profile 10 completo corregido

Comando:

```txt
python scripts\stress_local.py --env-file .local\staging_real_services_smoke_LOCAL_ONLY.env --profile 10 --workflow-mode interleaved --run-id real_stress10_final_20260705 --output evidence\slice_runs\real_services_stress_profile10_final_20260705.json
```

Resultado:

```txt
profile: 10
workflow_mode: interleaved
target.businesses: 20
target.orders: 200
target.marketplace_searches: 200
actual.businesses: 20
actual.ads: 200
actual.orders: 200
actual.workflow_orders: 20
total_requests: 916
total_errors: 0
total_error_rate: 0.0
duration_seconds: 4888.409
throughput_per_second: 0.1874
p50_ms: 4848.0594
p95_ms: 7063.2572
p99_ms: 9980.9817
steps_recorded: 937
exit_code: 0
```

Invariant violations:

```txt
idempotency_duplicates: 0
idempotency_replay_conflicts: 0
double_credit_consumption: 0
double_credit_accreditation: 0
negative_balances: 0
invalid_transitions: 0
redis_failures: 0
db_errors: 0
timeouts: 0
deadlocks: 0
job_lock_failures: 0
```

Notas:

- Los `409 Conflict` observados en `POST /api/v1/orders` son esperados dentro del harness: se prueba replay de idempotencia con payload distinto y luego replay correcto.
- El JSON final confirma `idempotency_replay_conflicts: 0` y `idempotency_duplicates: 0`.
- No hubo `ORDER_EXPIRED`, `SESSION_EXPIRED`, `RATE_LIMITED`, `DuplicatePreparedStatement`, `UniqueViolation`, 5xx ni stack traces.

Evidencia:

```txt
evidence/slice_runs/real_services_stress_profile10_final_20260705.json
evidence/slice_runs/real_services_stress_profile10_final_20260705.log
```

## Gate 6 - Post-profile10 schema/Redis real

Comando:

```txt
python scripts\validate_local_schema.py --env-file .local\staging_real_services_smoke_LOCAL_ONLY.env --output evidence\slice_runs\real_services_profile10_final_post_schema_20260705.json
```

Resultado:

```txt
table_count: 23
index_count: 128
redis_ping: True
failures: []
exit_code: 0
```

Evidencia:

```txt
evidence/slice_runs/real_services_profile10_final_post_schema_20260705.json
```

## Secret/private scan

Artefactos escaneados:

```txt
evidence/slice_runs/real_services_stress_profile10_final_20260705.json
evidence/slice_runs/real_services_stress_profile10_final_20260705.log
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
```

Resultado:

```txt
forbidden_hits: 0
```

## Decision recomendada

```txt
REAL_SERVICES_SCHEMA_READY
REAL_SERVICES_SMOKE_READY
REAL_SERVICES_STRESS_CAP5X25_READY
REAL_SERVICES_PROFILE10_READY_AFTER_FIXES
NOT_READY_FOR_REAL_USE
```

## Riesgos residuales

- No hay deploy todavia.
- Railway backend staging pendiente.
- Cloudflare Pages frontend staging pendiente.
- Telegram real pendiente.
- Stripe live pendiente.
- Profile 25/50/100 contra servicios reales no ejecutado.
- La latencia real de staging fue alta: p95 aproximado 7s en profile10. Esto es aceptable como smoke/stress gobernado, pero no como experiencia final sin medir deploy real y region/configuracion.

## Siguiente paso recomendado

Avanzar a deploy staging gobernado:

1. Railway backend con variables reales de staging.
2. Migraciones/ready check contra Supabase desde entorno deployado.
3. Cloudflare Pages frontend apuntando al backend staging.
4. Smoke Telegram real.
5. Smoke Stripe test mode.
6. Repetir stress ligero desde staging deployado antes de cualquier piloto.
