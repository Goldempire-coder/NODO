# Real Services Profile 25 Attempt - 2026-07-08

## Estado

TIMEOUT_WITH_ZERO_ERRORS

No es `READY_FOR_REAL_USE`.

## Objetivo

Ejecutar `profile 25` contra servicios reales despues de las optimizaciones de rutas lentas.

El perfil contractual del harness para `profile 25` es:

- `50` negocios
- `500` ordenes
- `500` busquedas marketplace
- `50` eventos Stripe/manual review

## Run 1: profile 25 completo sin limite

Run id:

- `real_services_profile25_after_jobs_20260708_200000`

Resultado:

- El run fue detenido manualmente despues de una duracion excesiva.
- No alcanzo a escribir JSON final.
- Al limpiar, se encontro que solo habia llegado a preparar:
  - `50` negocios
  - `50` submissions
  - `50` access links
  - `50` payment methods
  - `50` wallets
  - `15` ads
  - `0` ordenes

Cleanup:

- `evidence/slice_runs/cleanup_dry_run_real_services_profile25_after_jobs_20260708_200000.json`
- `evidence/slice_runs/cleanup_execute_real_services_profile25_after_jobs_20260708_200000.json`
- `evidence/slice_runs/cleanup_postcheck_real_services_profile25_after_jobs_20260708_200000.json`

Postcheck:

- Entidades operativas vivas: `0`
- Usuarios y audit logs quedan retenidos por diseno append-only.

## Run 2: profile 25 acotado a 600 segundos

Run id:

- `real_services_profile25_bounded_20260708_203500`

Archivos:

- `evidence/slice_runs/real_services_profile25_bounded_20260708_203500.json`
- `evidence/slice_runs/real_services_profile25_bounded_20260708_203500.checkpoint.json`

Resultado:

- Estado: `timeout`
- Exit code: `2`
- Error: `stress exceeded 600s during seed_businesses`
- Duracion: `620.194 s`
- Requests: `182`
- Errores: `0`
- Error rate: `0.0`
- p50: `2982.6078 ms`
- p95: `4803.595 ms`
- p99: `9634.5524 ms`

Progreso alcanzado:

- `18 / 50` negocios
- `0` ads
- `0` ordenes
- `0` workflow orders
- Fase: `seed_businesses`

Invariantes:

- `idempotency_duplicates`: `0`
- `idempotency_replay_conflicts`: `0`
- `double_credit_consumption`: `0`
- `double_credit_accreditation`: `0`
- `negative_balances`: `0`
- `invalid_transitions`: `0`
- `redis_failures`: `0`
- `db_errors`: `0`
- `timeouts`: `0`
- `deadlocks`: `0`
- `job_lock_failures`: `0`

Rutas mas lentas del bounded run:

- `POST /api/v1/businesses/{id}/submit-verification`
  - count: `18`
  - avg: `4490.6724 ms`
  - p95: `5136.8919 ms`
  - p99: `5190.6295 ms`
- `POST /api/v1/admin/businesses/{id}/access-links`
  - count: `18`
  - avg: `3668.0184 ms`
  - p95: `4170.7138 ms`
  - p99: `4803.595 ms`
- `POST /api/v1/admin/businesses/{id}/approve`
  - count: `18`
  - avg: `3534.7116 ms`
  - p95: `3938.9028 ms`
  - p99: `4084.7348 ms`
- `POST /api/v1/admin/credits/adjust`
  - count: `18`
  - avg: `3463.8561 ms`
  - p95: `3837.9482 ms`
  - p99: `4197.8703 ms`
- `POST /api/v1/businesses`
  - count: `18`
  - avg: `3048.6929 ms`
  - p95: `3365.0929 ms`
  - p99: `3605.2279 ms`
- `POST /api/v1/businesses/{id}/verification-documents`
  - count: `72`
  - avg: `2764.0354 ms`
  - p95: `3048.7578 ms`
  - p99: `9678.8255 ms`
- `POST /api/v1/auth/telegram`
  - count: `20`
  - avg: `2236.1505 ms`
  - p95: `2539.421 ms`
  - p99: `2964.2538 ms`

Cleanup:

- `evidence/slice_runs/cleanup_dry_run_real_services_profile25_bounded_20260708_203500.json`
- `evidence/slice_runs/cleanup_execute_real_services_profile25_bounded_20260708_203500.json`
- `evidence/slice_runs/cleanup_postcheck_real_services_profile25_bounded_20260708_203500.json`

Postcheck:

- Entidades operativas vivas: `0`
- Usuarios y audit logs quedan retenidos por diseno append-only.

## Interpretacion

El sistema no mostro errores ni violaciones de invariantes durante la parte ejecutada del profile 25 real.

Pero profile 25 completo no es operativo todavia contra estos servicios reales. El cuello aparece antes de llegar al marketplace y a ordenes: preparar/verificar/aprobar/vincular negocios y subir documentos reales consume demasiado tiempo.

Esto significa:

- Estabilidad parcial: buena en el tramo ejecutado.
- Integridad: buena en el tramo ejecutado.
- Rendimiento/capacidad para profile 25 completo: no aprobado.
- No hay evidencia aun de `500` ordenes reales bajo este perfil, porque el harness no llego a esa fase.

## Recomendacion

Antes de repetir profile 25 completo, conviene separar el problema:

1. Crear un seed real reutilizable o mas liviano para negocios aprobados, sin repetir 4 uploads + submit + approve + access link en cada stress.
2. Perfilar `submit-verification`, `approve`, `access-links`, `credits/adjust` y upload de documentos, porque cada negocio tarda demasiado.
3. Correr un stress enfocado en ordenes usando negocios/anuncios ya preparados, para medir el flujo que realmente importa al cliente sin pagar todo el costo de onboarding en cada run.
4. Solo despues repetir profile 25 completo end-to-end.

## Validacion local posterior

No se modifico codigo en este intento. La validacion de codigo completa ya habia pasado antes de esta corrida:

- `ruff`: PASS
- `compileall`: PASS
- `pytest`: `129 passed, 1 warning`

