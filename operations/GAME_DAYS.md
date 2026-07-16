# GAME_DAYS

Estado: REQUIRED, NOT RUN
Ultima actualizacion: 2026-07-11

## Simulacion 1: API lenta

- Objetivo: validar `API_LATENCY_RUNBOOK`.
- Entorno: staging.
- Riesgo: bajo si no muta datos.
- Aborto: 5xx sostenido o impacto a usuarios reales.
- Procedimiento: ejecutar carga marketplace controlada y revisar p95.
- Metricas: p50/p95/p99, 5xx, readiness.
- Estado: NOT RUN.

## Simulacion 2: Webhook duplicado

- Objetivo: validar idempotencia Telegram/Stripe/onchain.
- Entorno: staging con datos sinteticos.
- Riesgo: medio.
- Aborto: credito duplicado o datos reales afectados.
- Estado: NOT RUN.

## Simulacion 3: Storage privado falla

- Objetivo: validar runbook storage.
- Entorno: staging.
- Riesgo: bajo con objeto sintetico.
- Procedimiento: `staging_storage_smoke.py`.
- Estado: NOT RUN.

## Simulacion 4: Deploy defectuoso

- Objetivo: validar rollback.
- Entorno: staging.
- Riesgo: medio.
- Aborto: rollback no disponible.
- Estado: BLOCKED por falta de rollback provider documentado.

## Simulacion 5: Restore DB

- Objetivo: probar recuperacion Postgres.
- Entorno: staging aislado.
- Riesgo: alto.
- Estado: BLOCKED para ejecucion.
- Contrato/SOP: definido en slice 31B, no validado.
- Fase futura: 31D restore drill staging/isolated.

## Simulacion 6: Restore storage privado

- Objetivo: validar recuperacion Supabase Storage privado y reconciliacion con `file_assets`.
- Entorno: staging aislado con objetos sinteticos.
- Riesgo: medio.
- Estado: BLOCKED para ejecucion.
- Contrato/SOP: `sops/STORAGE_RESTORE_SOP.md`.
- Fase futura: 31D/31E.

## Simulacion 7: Secrets recovery

- Objetivo: validar que secrets/env vars pueden recuperarse y rotarse sin imprimir secretos.
- Entorno: staging.
- Riesgo: medio.
- Estado: BLOCKED para ejecucion.
- Contrato/SOP: `sops/SECRETS_RECOVERY_SOP.md`.
- Fase futura: 31D/31F.
