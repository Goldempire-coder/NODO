# Real Services Internal Order Profile - 2026-07-08

## Estado

PASSED_WITH_INTERNAL_BOTTLENECKS

No es `READY_FOR_REAL_USE`.

## Objetivo

Perfilar con servicios reales los puntos lentos detectados en:

- `POST /api/v1/orders`
- `POST /api/v1/business/orders/{id}/confirm-payment`

La meta no fue aumentar carga, sino ubicar el costo interno antes de seguir subiendo perfiles.

## Cambios realizados

- `scripts/local_hardening_common.py`
  - Agrega metricas agrupadas por ruta canonica (`route_groups`).
- `scripts/local_smoke.py`
  - Normaliza rutas para metricas.
  - Captura perfiles internos `_profile` sin exponerlos como payload funcional.
- `scripts/stress_local.py`
  - Agrega `profiled_steps` al JSON final del stress.
- `apps/api/app/modules/orders/service.py`
  - Agrega profiling interno opt-in con `NODO_INTERNAL_PROFILING=1`.
  - Agrega perfiles para `create_order` y `confirm_business_payment`.
  - Agrega profiling interno para `upload_payment_evidence`.
  - Evita el update redundante de `ad.status = in_order` cuando el repositorio Postgres ya lo hace de forma transaccional.
  - Evita prefetch duplicado de orden, payment report y anuncio en `confirm-payment` cuando se usa el repositorio atomico Postgres.
  - Separa profiling de `service:business_access` y `service:rate_limit`.
  - Escribe en batch los tres audit events de confirmacion (`payment_confirmed`, `credits_consumed`, `ad_archived`) cuando el audit writer lo soporta.
- `apps/api/app/modules/orders/repository.py`
  - Declara `moves_ad_on_create_order`.
  - Agrega perfiles de subpasos SQL dentro de la confirmacion de pago.
- `apps/api/app/modules/businesses/access_control.py`
  - Usa acceso combinado negocio + link cuando el repositorio lo soporta.
- `apps/api/app/modules/businesses/repository.py`
  - Agrega `get_business_with_latest_access_link_for_owner` para compactar el gate de Mini App Negocio en Postgres.
- `apps/api/app/shared/audit/audit_service.py`
  - Agrega `write_many` para audit writer in-memory y Postgres.
  - Mantiene auditoria append-only, pero reduce tres inserts secuenciales a un insert batch.
- `apps/api/app/shared/idempotency/store.py`
  - Optimiza Redis idempotency para guardar la respuesta y liberar el lock en una sola llamada Lua atomica.
- `apps/api/app/shared/storage/private.py`
  - Reutiliza el `httpx.Client` del adaptador Supabase Storage en vez de crear/cerrar uno por operacion.
- `apps/api/app/modules/jobs/worker.py`
  - Agrega profiling interno opt-in para `expire_and_escalate_orders`.
  - Para `dry_run=True`, mantiene Redis lock pero crea un solo `job_run` terminal al final, en vez de crear `started` y luego actualizar a terminal.
  - No cambia el path mutable del job real.
- `apps/api/app/modules/jobs/service.py`
  - Agrega profiling interno del endpoint admin dry-run.

## Runs ejecutados

### 1. Route-level profiling

Archivo:

- `evidence/slice_runs/real_services_profile_route_profiling_cap5_20260708_161005.json`

Resultado:

- Requests: `60`
- Errors: `0`
- Duration: `283.149s`
- p50: `4080.7774 ms`
- p95: `7175.403 ms`
- p99: `7260.0802 ms`

Rutas lentas:

- `POST /api/v1/orders`: avg `6446.1432 ms`, p95 `7405.6928 ms`
- `POST /api/v1/business/orders/{id}/confirm-payment`: avg `6892.958 ms`, p95 `7260.0802 ms`
- `POST /api/v1/admin/jobs/expire-and-escalate-orders/dry-run`: p95 `7175.403 ms`

Cleanup:

- `evidence/slice_runs/cleanup_postcheck_real_services_profile_route_profiling_cap5_20260708_161005.json`
- Postcheck: `0` registros vivos del run en entidades sinteticas rastreadas.

### 2. Internal profiling antes del fix

Archivo:

- `evidence/slice_runs/real_services_internal_profile_orders_min_20260708_164708.json`

Resultado:

- Requests: `23`
- Errors: `0`
- Duration: `116.88s`
- p50: `4312.0943 ms`
- p95: `7223.6612 ms`
- p99: `13248.352 ms`

Hallazgos internos:

- `stress:orders:create:0`
  - route latency: `5986.4237 ms`
  - profile total: `4720.7675 ms`
  - `service:get_existing_idempotency`: `1061.4551 ms`
  - `audit:order_created_and_ad_moved`: `480.8886 ms`
  - `repo:set_ad_in_order_redundant`: `427.1351 ms`
  - `service:get_ad`: `415.0375 ms`
- `stress:orders:create:1`
  - route latency: `5927.8681 ms`
  - profile total: `4481.0659 ms`
  - `service:get_existing_idempotency`: `949.634 ms`
  - `service:get_ad`: `591.3768 ms`
  - `audit:order_created_and_ad_moved`: `478.0741 ms`
  - `service:count_active_orders`: `459.7263 ms`
- `stress:confirm:0`
  - route latency: `6332.148 ms`
  - profile total: `4667.4335 ms`
  - `service:business_access_and_rate_limit`: `1547.5394 ms`
  - `repo:confirm_payment_atomic`: `942.336 ms`
  - `audit:confirm_credits_ad`: `738.2545 ms`
  - `repo:get_order_for_business`: `401.5496 ms`

Cleanup:

- `evidence/slice_runs/cleanup_postcheck_real_services_internal_profile_orders_min_20260708_164708.json`
- Postcheck: `0` registros vivos del run en entidades sinteticas rastreadas.

### 3. Internal profiling despues del fix seguro

Archivo:

- `evidence/slice_runs/real_services_internal_profile_orders_min_after_fix_20260708_165036.json`

Resultado:

- Requests: `23`
- Errors: `0`
- Duration: `113.608s`
- p50: `4213.7416 ms`
- p95: `7722.0561 ms`
- p99: `8176.0772 ms`

Hallazgos internos:

- `stress:orders:create:0`
  - route latency: `6023.9998 ms`
  - profile total: `4760.9431 ms`
  - `service:get_existing_idempotency`: `1349.683 ms`
  - `audit:order_created_and_ad_moved`: `890.3341 ms`
  - `repo:create_order_and_move_ad`: `566.5285 ms`
  - `repo:add_state_event`: `452.067 ms`
- `stress:orders:create:1`
  - route latency: `6808.5017 ms`
  - profile total: `4820.0508 ms`
  - `service:get_existing_idempotency`: `1407.05 ms`
  - `audit:order_created_and_ad_moved`: `621.9384 ms`
  - `repo:create_order_and_move_ad`: `441.9307 ms`
  - `service:count_active_orders`: `420.573 ms`
- `stress:confirm:0`
  - route latency: `7722.0561 ms`
  - profile total: `6602.2938 ms`
  - `service:business_access_and_rate_limit`: `1928.2679 ms`
  - `repo:confirm_payment_atomic`: `1624.8684 ms`
  - `audit:confirm_credits_ad`: `1193.5096 ms`
  - `repo:get_submitted_payment_report`: `565.4434 ms`
  - `repo:get_ad`: `369.1808 ms`

Cleanup:

- `evidence/slice_runs/cleanup_postcheck_real_services_internal_profile_orders_min_after_fix_20260708_165038.json`
- Postcheck: `0` registros vivos del run en entidades sinteticas rastreadas.

### 4. Internal profiling despues del fix de prefetch en confirm-payment

Archivo:

- `evidence/slice_runs/real_services_internal_profile_confirm_prefetch_fix_20260708_171000.json`

Resultado:

- Requests: `23`
- Errors: `0`
- Duration: `116.449s`
- p50: `4123.9804 ms`
- p95: `7176.8821 ms`
- p99: `7667.7664 ms`

Ruta objetivo:

- `POST /api/v1/business/orders/{id}/confirm-payment`
  - route latency: `6099.0643 ms`
  - profile total: `5003.8169 ms`
  - `service:business_access_and_rate_limit`: `1497.367 ms`
  - `repo:confirm_payment_atomic`: `1692.1323 ms`
  - `repo:add_state_event`: `297.973 ms`
  - `audit:confirm_credits_ad`: `916.2989 ms`

Comparacion contra el run anterior:

- Antes: `confirm-payment` route latency `7722.0561 ms`.
- Despues: `confirm-payment` route latency `6099.0643 ms`.
- Mejora observada: aproximadamente `1622.9918 ms`.
- Los prefetches externos `repo:get_order_for_business`, `repo:get_submitted_payment_report` y `repo:get_ad` ya no aparecen como etapas separadas antes de la transaccion atomica.

Cleanup:

- `evidence/slice_runs/cleanup_postcheck_real_services_internal_profile_confirm_prefetch_fix_20260708_171000.json`
- Postcheck operativo: `0` negocios, anuncios, ordenes, payment reports, file assets y entidades operativas vivas.
- Quedan `3` usuarios y `35` audit logs retenidos por diseno append-only.

### 5. Internal profiling despues del fix de business access

Archivo:

- `evidence/slice_runs/real_services_internal_profile_business_access_fix_20260708_172000.json`

Resultado:

- Requests: `23`
- Errors: `0`
- Duration: `104.449s`
- p50: `3879.4356 ms`
- p95: `6705.8997 ms`
- p99: `7853.3482 ms`

Ruta objetivo:

- `POST /api/v1/business/orders/{id}/confirm-payment`
  - route latency: `6140.4265 ms`
  - profile total: `4696.0416 ms`
  - `service:business_access`: `1355.1126 ms`
  - `service:rate_limit`: `344.1311 ms`
  - `repo:confirm_payment_atomic`: `1275.7524 ms`
  - `repo:add_state_event`: `280.3655 ms`
  - `audit:confirm_credits_ad`: `1169.8806 ms`

Interpretacion puntual:

- El gate ahora separa acceso y rate limit en la evidencia.
- La query combinada redujo viajes logicos, pero la latencia remota de Supabase sigue dejando `business_access` alrededor de `1.35s`.
- La transaccion atomica bajo de `1692.1323 ms` a `1275.7524 ms` en este run.
- El costo de auditoria sigue alto: `audit:confirm_credits_ad` quedo en `1169.8806 ms`.

Cleanup:

- `evidence/slice_runs/cleanup_postcheck_real_services_internal_profile_business_access_fix_20260708_172000.json`
- Postcheck operativo: `0` negocios, anuncios, ordenes, payment reports, file assets y entidades operativas vivas.
- Quedan `3` usuarios y `35` audit logs retenidos por diseno append-only.

### 6. Internal profiling despues del fix de batch audit

Archivo:

- `evidence/slice_runs/real_services_internal_profile_audit_batch_fix_20260708_173000.json`

Resultado:

- Requests: `23`
- Errors: `0`
- Duration: `127.838s`
- p50: `4726.9161 ms`
- p95: `8312.075 ms`
- p99: `10640.9293 ms`

Ruta objetivo:

- `POST /api/v1/business/orders/{id}/confirm-payment`
  - route latency: `4485.7191 ms`
  - profile total: `3083.6498 ms`
  - `service:business_access`: `834.4914 ms`
  - `service:rate_limit`: `225.7309 ms`
  - `repo:confirm_payment_atomic`: `1240.8966 ms`
  - `repo:add_state_event`: `194.0918 ms`
  - `audit:confirm_credits_ad`: `318.0236 ms`

Comparacion contra el run anterior:

- Antes: `audit:confirm_credits_ad` `1169.8806 ms`.
- Despues: `audit:confirm_credits_ad` `318.0236 ms`.
- Mejora observada en auditoria: aproximadamente `851.857 ms`.
- Antes del trabajo de optimizacion: `confirm-payment` route latency `7722.0561 ms`.
- Despues del batch audit: `confirm-payment` route latency `4485.7191 ms`.
- Mejora observada en la ruta objetivo desde el baseline comparable: aproximadamente `3236.337 ms`.

Rutas lentas restantes en este run:

- `POST /api/v1/orders/{id}/payment-evidence`: `10640.9293 ms`.
- `POST /api/v1/admin/jobs/expire-and-escalate-orders/dry-run`: `8312.075 ms`.
- `POST /api/v1/businesses`: `6985.097 ms`.
- `POST /api/v1/orders`: p95 `6935.0902 ms`.
- `POST /api/v1/business/ads`: p95 `6629.7873 ms`.

Cleanup:

- `evidence/slice_runs/cleanup_postcheck_real_services_internal_profile_audit_batch_fix_20260708_173000.json`
- Postcheck operativo: `0` sesiones, negocios, access links, payment methods, credit wallets, ads, ledger, ordenes, state events, payment reports, messages, disputes, credit purchases, referrals, notification jobs, intake requests y file assets.
- Quedan `3` usuarios y `35` audit logs retenidos por diseno append-only.

### 7. Internal profiling de payment-evidence antes de optimizar storage

Archivo:

- `evidence/slice_runs/real_services_internal_profile_payment_evidence_20260708_180000.json`

Resultado:

- Requests: `23`
- Errors: `0`
- Duration: `115.943s`
- p50: `4207.0437 ms`
- p95: `7888.6021 ms`
- p99: `9841.3 ms`

Ruta objetivo:

- `POST /api/v1/orders/{id}/payment-evidence`
  - route latency: `4489.7981 ms`
  - profile total: `3288.7835 ms`
  - `service:auth_and_rate_limit`: `139.2073 ms`
  - `repo:get_order`: `644.9595 ms`
  - `storage:store_payment_evidence`: `933.736 ms`
  - `repo:create_payment_evidence_file`: `285.4977 ms`
  - `audit:payment_evidence_uploaded`: `287.9739 ms`
  - `service:idempotency_replay_or_store`: `3149.4855 ms`

Nota: `service:idempotency_replay_or_store` envuelve el compute interno, por lo que no debe sumarse con las etapas hijas. La diferencia entre el total y las etapas hijas apunta a costos de Redis/idempotency y red remota.

Cleanup:

- `evidence/slice_runs/cleanup_postcheck_real_services_internal_profile_payment_evidence_20260708_180000.json`
- Postcheck operativo: `0` entidades operativas vivas; quedan `3` usuarios y `35` audit logs retenidos por diseno append-only.

### 8. Internal profiling despues del fix Redis idempotency

Archivo:

- `evidence/slice_runs/real_services_internal_profile_payment_evidence_idempotency_fix_20260708_181500.json`

Resultado:

- Requests: `23`
- Errors: `0`
- Duration: `109.308s`
- p50: `3919.9112 ms`
- p95: `7269.0736 ms`
- p99: `10952.9596 ms`

Ruta objetivo:

- `POST /api/v1/orders/{id}/payment-evidence`
  - route latency: `10952.9596 ms`
  - profile total: `9833.4891 ms`
  - `service:auth_and_rate_limit`: `332.7956 ms`
  - `repo:get_order`: `576.9357 ms`
  - `storage:store_payment_evidence`: `7878.204 ms`
  - `repo:create_payment_evidence_file`: `233.7265 ms`
  - `audit:payment_evidence_uploaded`: `287.8641 ms`
  - `service:idempotency_replay_or_store`: `9500.5955 ms`

Interpretacion:

- El fix Redis no produjo un falso verde por si solo.
- Este run mostro un spike claro de Supabase Storage: `storage:store_payment_evidence` subio a `7878.204 ms`.
- No hubo errores ni violaciones de invariantes, pero la latencia confirma que storage remoto puede dominar la ruta.

Cleanup:

- `evidence/slice_runs/cleanup_postcheck_real_services_internal_profile_payment_evidence_idempotency_fix_20260708_181500.json`
- Postcheck operativo: `0` entidades operativas vivas; quedan `3` usuarios y `35` audit logs retenidos por diseno append-only.

### 9. Internal profiling despues del fix de cliente HTTP persistente para Supabase Storage

Archivo:

- `evidence/slice_runs/real_services_internal_profile_payment_evidence_storage_client_fix_20260708_183000.json`

Resultado:

- Requests: `23`
- Errors: `0`
- Duration: `101.213s`
- p50: `4044.6466 ms`
- p95: `6512.3141 ms`
- p99: `7193.7898 ms`

Ruta objetivo:

- `POST /api/v1/orders/{id}/payment-evidence`
  - route latency: `2777.8838 ms`
  - profile total: `1845.8794 ms`
  - `service:auth_and_rate_limit`: `126.8542 ms`
  - `repo:get_order`: `221.7219 ms`
  - `storage:store_payment_evidence`: `403.256 ms`
  - `repo:create_payment_evidence_file`: `241.6856 ms`
  - `audit:payment_evidence_uploaded`: `285.2068 ms`
  - `service:idempotency_replay_or_store`: `1718.927 ms`

Comparacion:

- Run inicial de `payment-evidence`: route latency `4489.7981 ms`.
- Run con spike remoto: route latency `10952.9596 ms`.
- Run despues de cliente HTTP persistente: route latency `2777.8838 ms`.
- Storage bajo de `933.736 ms` en el primer run y `7878.204 ms` en el spike a `403.256 ms` en el run posterior.

Cleanup:

- `evidence/slice_runs/cleanup_postcheck_real_services_internal_profile_payment_evidence_storage_client_fix_20260708_183000.json`
- Postcheck operativo: `0` entidades operativas vivas; quedan `3` usuarios y `35` audit logs retenidos por diseno append-only.

### 10. Internal profiling de business ads

Archivo inicial:

- `evidence/slice_runs/real_services_internal_profile_business_ads_20260708_184500.json`

Resultado inicial:

- Requests: `23`
- Errors: `0`
- Duration: `101.753s`
- p50: `4102.5227 ms`
- p95: `6067.1463 ms`
- p99: `7560.718 ms`

Ruta objetivo inicial:

- `POST /api/v1/business/ads`
  - count: `2`
  - error_count: `0`
  - p50: `4510.8515 ms`
  - p95: `4618.2608 ms`
  - avg: `4564.5562 ms`

Etapas internas iniciales:

- `stress:ads:create:0`
  - route latency: `4510.8515 ms`
  - profile total: `3218.1636 ms`
  - `service:business_access`: `693.2044 ms`
  - `service:get_payment_method`: `498.3491 ms`
  - `repo:has_overlapping_ad`: `368.0011 ms`
  - `repo:publish_ad`: `809.8925 ms`
  - `audit:ad_created_published_credits`: `342.14 ms`
  - `service:idempotency_replay_or_store`: `2288.7018 ms`
- `stress:ads:create:1`
  - route latency: `4618.2608 ms`
  - profile total: `3666.7285 ms`
  - `service:business_access`: `767.0068 ms`
  - `service:get_payment_method`: `446.963 ms`
  - `repo:has_overlapping_ad`: `270.2496 ms`
  - `repo:publish_ad`: `1117.5492 ms`
  - `audit:ad_created_published_credits`: `613.2642 ms`
  - `service:idempotency_replay_or_store`: `2848.2678 ms`

Cleanup inicial:

- `evidence/slice_runs/cleanup_postcheck_real_services_internal_profile_business_ads_20260708_184500.json`
- Postcheck operativo: `0` entidades operativas vivas; quedan `3` usuarios y `35` audit logs retenidos por diseno append-only.

### 11. Internal profiling de business ads despues de optimizar idempotency lock

Archivo:

- `evidence/slice_runs/real_services_internal_profile_business_ads_idempotency_fix_20260708_185500.json`

Resultado:

- Requests: `23`
- Errors: `0`
- Duration: `99.839s`
- p50: `3659.8993 ms`
- p95: `5708.682 ms`
- p99: `9772.5312 ms`

Ruta objetivo:

- `POST /api/v1/business/ads`
  - count: `2`
  - error_count: `0`
  - p50: `4007.1833 ms`
  - p95: `4308.4301 ms`
  - avg: `4157.8067 ms`

Etapas internas posteriores:

- `stress:ads:create:0`
  - route latency: `4007.1833 ms`
  - profile total: `2963.6173 ms`
  - `service:business_access`: `1059.6057 ms`
  - `service:get_payment_method`: `316.9288 ms`
  - `repo:has_overlapping_ad`: `279.5641 ms`
  - `repo:publish_ad`: `691.6235 ms`
  - `audit:ad_created_published_credits`: `304.0515 ms`
  - `service:idempotency_replay_or_store`: `1700.965 ms`
- `stress:ads:create:1`
  - route latency: `4308.4301 ms`
  - profile total: `3152.9428 ms`
  - `service:business_access`: `1190.8849 ms`
  - `service:get_payment_method`: `227.722 ms`
  - `repo:has_overlapping_ad`: `387.0473 ms`
  - `repo:publish_ad`: `743.2425 ms`
  - `audit:ad_created_published_credits`: `269.0479 ms`
  - `service:idempotency_replay_or_store`: `1796.6148 ms`

Comparacion:

- `POST /api/v1/business/ads` promedio bajo de `4564.5562 ms` a `4157.8067 ms`.
- `service:idempotency_replay_or_store` bajo de `2288.7018-2848.2678 ms` a `1700.965-1796.6148 ms`.
- La mejora no resuelve todo el costo: todavia pesan acceso negocio, publish transaccional y latencia Redis/DB remota.

Cleanup:

- `evidence/slice_runs/cleanup_postcheck_real_services_internal_profile_business_ads_idempotency_fix_20260708_185500.json`
- Postcheck operativo: `0` entidades operativas vivas; quedan `3` usuarios y `35` audit logs retenidos por diseno append-only.

### 12. Internal profiling de order create despues de state event transaccional

Archivo:

- `evidence/slice_runs/real_services_internal_profile_orders_create_tx_event_20260708_191000.json`

Resultado:

- Requests: `23`
- Errors: `0`
- Duration: `97.365s`
- p50: `3515.8843 ms`
- p95: `5678.5598 ms`
- p99: `7294.2974 ms`

Ruta objetivo:

- `POST /api/v1/orders`
  - count: `2`
  - error_count: `0`
  - p50: `4725.2136 ms`
  - p95: `5626.0286 ms`
  - avg: `5175.6211 ms`

Etapas internas posteriores:

- `stress:orders:create:0`
  - route latency: `5626.0286 ms`
  - profile total: `4052.4699 ms`
  - `service:auth_and_rate_limit`: `215.0416 ms`
  - `service:get_existing_idempotency`: `969.3799 ms`
  - `service:get_ad`: `345.9575 ms`
  - `service:get_business`: `409.9036 ms`
  - `service:count_active_orders`: `257.9104 ms`
  - `service:get_payment_method`: `229.799 ms`
  - `repo:create_order_and_move_ad`: `624.6334 ms`
  - `audit:order_created_and_ad_moved`: `920.2758 ms`
- `stress:orders:create:1`
  - route latency: `4725.2136 ms`
  - profile total: `3446.0653 ms`
  - `service:auth_and_rate_limit`: `95.8954 ms`
  - `service:get_existing_idempotency`: `1150.2705 ms`
  - `service:get_ad`: `258.9886 ms`
  - `service:get_business`: `226.8797 ms`
  - `service:count_active_orders`: `213.3867 ms`
  - `service:get_payment_method`: `626.7618 ms`
  - `repo:create_order_and_move_ad`: `564.1866 ms`
  - `audit:order_created_and_ad_moved`: `255.7146 ms`

Comparacion:

- En el run anterior comparable, `POST /api/v1/orders` estaba en `5553.4253 ms` promedio.
- Despues del state event transaccional, bajo a `5175.6211 ms` promedio.
- El stage separado `repo:add_state_event` ya no aparece en `profiled_steps`.
- Quedan costos variables importantes: `service:get_existing_idempotency`, `audit:order_created_and_ad_moved`, lecturas previas y latencia remota de Supabase.

Cleanup:

- `evidence/slice_runs/cleanup_postcheck_real_services_internal_profile_orders_create_tx_event_20260708_191000.json`
- Postcheck operativo: `0` entidades operativas vivas; quedan `3` usuarios y `35` audit logs retenidos por diseno append-only.

### 13. Internal profiling de jobs dry-run antes de optimizar job_run

Archivo:

- `evidence/slice_runs/real_services_internal_profile_jobs_dry_run_20260708_192000.json`

Ruta:

- `POST /api/v1/admin/jobs/expire-and-escalate-orders/dry-run`
  - count: `1`
  - errors: `0`
  - latency: `9893.2032 ms`
  - profile total: `8146.8083 ms`

Etapas internas:

- `service:auth_and_rate_limit`: `489.9773 ms`
- `worker:run_dry_run`: `7015.1376 ms`
- `audit:job_dry_run_executed`: `337.6743 ms`
- `service:idempotency_replay_or_store`: `7765.6579 ms`

Worker profile:

- `lock:acquire`: `1887.5428 ms`
- `repo:create_job_run_started`: `1078.856 ms`
- `audit:job_started`: `545.271 ms`
- `worker:process_orders`: `1628.6408 ms`
- `worker:process_ads`: `275.0376 ms`
- `worker:process_founders`: `594.1105 ms`
- `repo:update_job_run_terminal`: `440.1037 ms`
- `audit:job_finished`: `431.3485 ms`
- `lock:release`: `134.0317 ms`

Interpretacion:

- El dry-run estaba pagando costos de un job real: `job_started`, `job_finished` y doble escritura `job_runs`.
- El contrato exige lock y trazabilidad, pero el dry-run no necesita emitir los mismos eventos de inicio/fin que una corrida mutable.

Cleanup:

- `evidence/slice_runs/cleanup_postcheck_real_services_internal_profile_jobs_dry_run_20260708_192000.json`
- Postcheck operativo: `0` entidades operativas vivas; quedan usuarios y audit logs retenidos por diseno append-only.

### 14. Internal profiling de jobs dry-run despues de job_run terminal unico

Archivo:

- `evidence/slice_runs/real_services_internal_profile_jobs_dry_run_terminal_run_20260708_193000.json`

Ruta:

- `POST /api/v1/admin/jobs/expire-and-escalate-orders/dry-run`
  - count: `1`
  - errors: `0`
  - latency: `5803.5752 ms`
  - profile total: `4592.9805 ms`

Etapas internas:

- `service:auth_and_rate_limit`: `186.7668 ms`
- `worker:run_dry_run`: `3948.9954 ms`
- `audit:job_dry_run_executed`: `280.5997 ms`
- `service:idempotency_replay_or_store`: `4406.1842 ms`

Worker profile:

- `lock:acquire`: `740.1269 ms`
- `worker:process_orders`: `2161.8488 ms`
- `worker:process_ads`: `285.5125 ms`
- `worker:process_founders`: `390.0536 ms`
- `repo:create_job_run_terminal_dry_run`: `256.9 ms`
- `lock:release`: `114.3848 ms`

Comparacion:

- Dry-run antes: `9893.2032 ms`.
- Dry-run despues: `5803.5752 ms`.
- Mejora observada: `4089.628 ms` menos en la ruta.
- Ya no aparecen `repo:create_job_run_started`, `audit:job_started`, `repo:update_job_run_terminal` ni `audit:job_finished` en el path dry-run.
- El lock Redis sigue activo y la auditoria admin `job_dry_run_executed` se mantiene.
- El siguiente costo real esta en `worker:process_orders` y latencia de Redis/servicios remotos, no en eventos de job_started/job_finished.

Cleanup:

- `evidence/slice_runs/cleanup_postcheck_real_services_internal_profile_jobs_dry_run_terminal_run_20260708_193000.json`
- Postcheck operativo: `0` entidades operativas vivas; quedan `3` usuarios y `33` audit logs retenidos por diseno append-only.

## Interpretacion

El sistema conserva integridad bajo estos runs:

- `0` errores HTTP.
- `0` violaciones de invariantes reportadas por el harness.
- Cleanup posterior sin residuos sinteticos vivos en tablas operativas.

Pero el rendimiento no esta listo para subir perfiles grandes sin optimizar. Los tiempos no vienen de un solo bug gigante; vienen de acumulacion de round trips remotos:

- checks de idempotencia persistente;
- acceso negocio + rate limit;
- lecturas previas de orden/payment report/ad;
- transaccion atomica de confirmacion;
- varias escrituras de audit/state events.

## Fix aplicado

Se elimino una escritura redundante de `ad.status = in_order` en `create_order` para Postgres. La creacion de orden ya mueve el anuncio en la misma operacion transaccional, asi que el segundo update no agregaba proteccion.

Evidencia: antes existia `repo:set_ad_in_order_redundant` con `307-427 ms`; despues ya no aparece en `profiled_steps`.

Tambien se elimino el prefetch duplicado de `order`, `payment_report` y `ad` antes de `confirm-payment` cuando el repositorio Postgres atomico ya valida y bloquea esas filas dentro de la transaccion.

Evidencia: `confirm-payment` bajo de `7722.0561 ms` a `6099.0643 ms` en el micro-run comparable.

Finalmente se compacto el gate de negocio y link de acceso para Postgres con `get_business_with_latest_access_link_for_owner`. Esto mantiene la misma politica, pero evita que el flujo tenga que pedir negocio y link en dos llamadas separadas cuando el repositorio puede devolver ambos.

Evidencia: el perfil ahora separa `service:business_access` (`1355.1126 ms`) y `service:rate_limit` (`344.1311 ms`). La ruta `confirm-payment` se mantiene alrededor de `6.1s`, asi que el siguiente ahorro grande no esta en el rate limit sino en auditoria/operaciones atomicas/latencia remota.

Despues se agrego batch audit para los tres eventos canonicos emitidos por `confirm-payment`: `payment_confirmed`, `credits_consumed` y `ad_archived`. No se elimino ningun evento; solo se cambio la forma de persistirlos cuando el audit writer Postgres soporta `write_many`.

Evidencia: `audit:confirm_credits_ad` bajo de `1169.8806 ms` a `318.0236 ms`, y la ruta `confirm-payment` bajo a `4485.7191 ms` en el micro-run posterior.

Quedan rutas lentas fuera del foco inicial. El run posterior mostro `payment-evidence` en `10640.9293 ms`, lo que apunta a costo de storage real/upload, y `admin/jobs/expire-and-escalate-orders/dry-run` en `8312.075 ms`. Tambien siguen altos `POST /api/v1/business/ads` y `POST /api/v1/orders`.

Para `payment-evidence`, se agrego profiling interno y se confirmo que el costo puede variar por Supabase Storage. Se optimizo:

- Redis idempotency: guarda respuesta y libera lock con una sola llamada Lua.
- Supabase Storage: reutiliza un `httpx.Client` persistente para evitar crear/cerrar cliente por operacion.

Evidencia: `payment-evidence` paso de `4489.7981 ms` en el primer run perfilado a `2777.8838 ms` despues del cliente HTTP persistente. Hubo un run intermedio con spike de storage (`7878.204 ms` solo en `storage:store_payment_evidence`), asi que la conclusion correcta es mejora observada con variabilidad remota todavia presente.

Para `business/ads`, se agrego profiling interno y batch audit para los eventos `ad_created`, `ad_published` y `credits_held`/`founder_free_use`. No se elimino ningun evento; solo se persisten juntos cuando el audit writer Postgres soporta `write_many`.

Tambien se compacto el primer paso de Redis idempotency con un Lua atomico que en una sola llamada revisa si existe replay y, si no existe, toma el lock. Esto mantiene el contrato de payload mismatch/replay y reduce round trips de la ruta nueva.

Evidencia: `POST /api/v1/business/ads` bajo de `4564.5562 ms` promedio a `4157.8067 ms`, y `service:idempotency_replay_or_store` bajo de `2288.7018-2848.2678 ms` a `1700.965-1796.6148 ms`.

Para `create_order`, se movio el `order_state_event` inicial al mismo commit Postgres que crea la orden y mueve el anuncio a `in_order`. En repositorios que no soportan eso, el flujo anterior sigue activo. Tambien se usa batch audit para `order_created` y `ad_moved_in_order`.

Evidencia: en `profiled_steps` ya no aparece `repo:add_state_event` para `POST /api/v1/orders`, y la ruta bajo de `5553.4253 ms` promedio a `5175.6211 ms` promedio en el micro-run posterior. Es una mejora moderada; no elimina la latencia principal.

Para `admin/jobs/expire-and-escalate-orders/dry-run`, se dejo el lock Redis y la trazabilidad, pero se elimino el costo de tratar el dry-run como job mutable completo. Ahora el dry-run crea un unico `job_run` terminal al final y conserva `job_dry_run_executed` como audit admin.

Evidencia: la ruta bajo de `9893.2032 ms` a `5803.5752 ms`. Ya no aparecen `job_started`/`job_finished` ni create+update de `job_runs` en el path dry-run.

## Validaciones

- `python -m ruff check apps\api scripts`: PASS
- `python -m compileall apps scripts`: PASS
- `python -m pytest apps\api\tests -q`: PASS, `129 passed, 1 warning`
- `corepack pnpm --filter @nodo/web build`: PASS

Warning conocido:

- `StarletteDeprecationWarning` por `httpx`/`TestClient`.

## Siguiente recomendacion

No recomiendo saltar todavia a `profile 200/500` contra servicios reales.

El siguiente paso tecnico debe ser optimizar los costos restantes alrededor de `confirm-payment` y anuncios:

1. Repetir `payment-evidence` en profile 25 real para validar si el cliente HTTP persistente sostiene la mejora bajo mas operaciones.
2. Volver a correr `business/ads`, `orders/create`, `confirm-payment` y `jobs dry-run` dentro de profile 25 real, porque los micro-runs mejoraron pero siguen por encima de una meta comoda.
3. Si `jobs dry-run` sigue alto en profile 25, perfilar `worker:process_orders` y separar costo de queries vs evaluacion en memoria.
4. Evaluar si se quiere seguir optimizando `POST /api/v1/orders` atacando `service:get_existing_idempotency` y audit, o si se acepta por ahora porque la ruta es de baja frecuencia frente a lecturas de marketplace.

Despues de eso, repetir:

- profile minimo interno;
- profile 25 real;
- profile 50 real;
- solo entonces volver a 100+.

