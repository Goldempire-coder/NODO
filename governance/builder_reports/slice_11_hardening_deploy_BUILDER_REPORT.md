# BUILDER_REPORT - slice_11_hardening_deploy

## Slice

- Slice: `slice_11_hardening_deploy`
- Fase autorizada: `LOCAL_HARDENING_AND_STRESS_ONLY`
- Estado final: `READY_FOR_OWNER_REVIEW`
- Fecha: 2026-07-04
- Builder/agente: Codex

## Scope construido

- Incluido:
  - Infra local Docker Compose para PostgreSQL y Redis.
  - Template `.env.local.example` seguro.
  - Configuracion runtime local para Postgres/Redis.
  - Storage privado local solo para hardening local opt-in.
  - Scripts de infra check, migraciones locales, rollback drill, schema validation, seed, smoke, stress y runner slice 11.
  - Tests de hardening local.
  - Evidencia JSON/MD.
- Excluido:
  - Supabase real.
  - Redis cloud real.
  - Storage real externo.
  - Stripe real/live.
  - Telegram real.
  - Deploy.
  - READY_FOR_REAL_USE.
- Que NO toque:
  - Reglas de negocio.
  - Estados/enums.
  - Features nuevas fuera de hardening/stress local.
  - Pagos reales.
  - Credenciales reales.

## Archivos y lineas

```txt
.gitignore:
lineas: 25
motivo: permitir versionar .env.local.example sin permitir .env.local real.
contrato cumplido: env template seguro sin secretos reales.
```

```txt
.env.local.example:
lineas: 1-30
motivo: template local-only para Postgres, Redis, secretos fake y storage local.
contrato cumplido: configuracion segura local.
```

```txt
docker-compose.local.yml:
lineas: 5, 22
motivo: servicios locales postgres:16-alpine y redis:7-alpine.
contrato cumplido: infra local Docker Compose sin Supabase/Redis cloud.
```

```txt
apps/api/app/core/config.py:
lineas: 51, 103
motivo: leer PRIVATE_STORAGE_MODE y PRIVATE_STORAGE_ROOT.
contrato cumplido: storage privado local controlado por env.
```

```txt
apps/api/app/shared/storage/private.py:
lineas: 69+
motivo: adapter LocalFilePrivateStorage para hardening local.
contrato cumplido: storage privado local sin exponer storage_path en signed URL.
```

```txt
apps/api/app/main.py:
lineas: 35, 85-86
motivo: activar LocalFilePrivateStorage solo con PRIVATE_STORAGE_MODE=local_file.
contrato cumplido: runtime normal sigue seguro sin simular storage publico.
```

```txt
scripts/local_hardening_common.py:
lineas: 15+
motivo: helpers compartidos de env local, redaccion, guard local DB y metricas.
contrato cumplido: scripts hardening consistentes y sin secretos en salida.
```

```txt
scripts/local_infra_check.py:
lineas: 24-44
motivo: verificar Docker, Compose, Postgres TCP, Redis TCP y env redacted.
contrato cumplido: evidencia de tooling local.
```

```txt
scripts/apply_local_migrations.py:
lineas: 15-43
motivo: aplicar migraciones 0001-0011 desde cero contra DB local.
contrato cumplido: migraciones reales locales.
```

```txt
scripts/rollback_local_migrations.py:
lineas: 15-46
motivo: rollback drill local 0011-0001 con guard contra DATABASE_URL no local.
contrato cumplido: rollback drill local viable.
```

```txt
scripts/validate_local_schema.py:
lineas: 53-89
motivo: validar tablas, indices y Redis ping.
contrato cumplido: schema real validado.
```

```txt
scripts/local_smoke.py:
lineas: 291-307
motivo: smoke E2E local con flujo 00-10 sobre Postgres/Redis.
contrato cumplido: API local no in-memory para hardening.
```

```txt
scripts/stress_local.py:
lineas: 216-235
motivo: harness stress progresivo con metricas e invariantes.
contrato cumplido: stress local inicial/progresivo.
```

```txt
scripts/seed_local_synthetic_data.py:
lineas: 11-16
motivo: dataset sintetico local sin datos reales.
contrato cumplido: seed local para pruebas progresivas.
```

```txt
scripts/run_slice_11_tests.py:
lineas: 66-78
motivo: runner slice 11 con pytest, infra, schema, frontend build, ruff, compileall y scan.
contrato cumplido: resultados de tests centralizados.
```

```txt
apps/api/tests/test_hardening_local.py:
lineas: 13-91
motivo: tests unitarios/static de env, compose, storage local, scripts y postura no real-use.
contrato cumplido: QA minima slice 11.
```

```txt
database/migrations/0006_slice_05_payment_instructions_reports.down.sql:
lineas: 11-13
motivo: rollback limpia file_assets de payment evidence antes de restaurar constraints previas.
contrato cumplido: migraciones reversibles con datos sinteticos.
```

```txt
database/migrations/0009_slice_08_credits_referrals.down.sql:
lineas: 20-22
motivo: rollback limpia ledger rows de slice 08 antes de restaurar credits_ledger_type_check anterior.
contrato cumplido: rollback local 0009 viable.
```

```txt
database/migrations/0010_slice_09_admin_console.down.sql:
lineas: 4-18
motivo: rollback limpia eventos/campos de resolucion admin antes de restaurar constraints previas.
contrato cumplido: rollback local 0010 viable.
```

```txt
evidence/slice_runs/slice_11_hardening_deploy_evidence.md:
lineas: 1+
motivo: evidencia consolidada local.
contrato cumplido: evidencia MD obligatoria.
```

```txt
evidence/slice_runs/slice_11_hardening_deploy_test_results.json:
lineas: n/a JSON
motivo: resultados automatizados del runner slice 11.
contrato cumplido: test results JSON obligatorio.
```

## Dependencias

- No se instalaron dependencias nuevas.
- Se usaron herramientas ya instaladas: Docker, Docker Compose, Python, pytest, ruff, compileall, corepack/pnpm.

## Contratos cumplidos

- Governance: no se declaro READY_FOR_REAL_USE; fase limitada a local hardening/stress.
- Data: migraciones `0001` a `0011` aplicadas desde cero contra Postgres local; rollback drill final OK.
- API: smoke cubrio health/ready/version y flujos API principales de slices 01-10 sobre runtime local Postgres/Redis.
- Security: env redacted, sin secretos reales, scan frontend sin hits, storage_path no expuesto, storage local opt-in.
- UI/UX: frontend build OK; no se construyeron pantallas nuevas.
- QA: runners 00-11 OK, pytest acumulado OK, ruff OK, compileall OK, smoke/stress/seed OK.

## Comandos ejecutados

```txt
comando: docker compose -f docker-compose.local.yml up -d
resultado: OK tras iniciar Docker Desktop.
evidencia: docker ps mostro postgres/redis healthy.
```

```txt
comando: python scripts\local_infra_check.py --env-file .env.local.example --require-services
resultado: OK; Docker 29.3.1, Docker Compose v5.1.0, Postgres TCP OK, Redis TCP OK.
evidencia: evidence/slice_runs/slice_11_local_infra_check.json
```

```txt
comando: python scripts\apply_local_migrations.py --env-file .env.local.example --reset
resultado: OK; 0001-0011 aplicadas.
evidencia: evidence/slice_runs/slice_11_local_migrations.json
```

```txt
comando: python scripts\validate_local_schema.py --env-file .env.local.example
resultado: OK; 23 tablas, 128 indices, Redis ping true.
evidencia: evidence/slice_runs/slice_11_local_schema_validation.json
```

```txt
comando: python scripts\local_smoke.py --env-file .env.local.example --run-id rollback-drill-smoke-3
resultado: OK; 28 requests, error rate 0.0, p50 122.8636 ms, p95 286.8681 ms, p99 291.8106 ms.
evidencia: evidence/slice_runs/slice_11_local_smoke.json
```

```txt
comando: python scripts\stress_local.py --env-file .env.local.example --profile 10 --cap-businesses 5 --cap-orders 10 --run-id stress10cap3
resultado: OK; 98 requests, error rate 0.0, p50 154.1572 ms, p95 307.3146 ms, p99 368.5465 ms.
evidencia: evidence/slice_runs/slice_11_local_stress.json
```

```txt
comando: python scripts\rollback_local_migrations.py --env-file .env.local.example
resultado: OK; rollback 0011-0001 con failures [].
evidencia: evidence/slice_runs/slice_11_local_rollback.json
```

```txt
comando: python scripts\seed_local_synthetic_data.py --env-file .env.local.example --businesses 2 --orders 4
resultado: OK; 35 requests, error rate 0.0, p50 224.4887 ms, p95 321.3889 ms, p99 400.2582 ms.
evidencia: evidence/slice_runs/slice_11_local_seed.json
```

```txt
comando: python scripts\run_slice_00_tests.py ... python scripts\run_slice_10_tests.py
resultado: OK; runners 00-10 con all_ok=True.
evidencia: evidence/slice_runs/slice_00_*_test_results.json a slice_10_*_test_results.json
```

```txt
comando: python scripts\run_slice_11_tests.py
resultado: OK; 7 checks OK.
evidencia: evidence/slice_runs/slice_11_hardening_deploy_test_results.json
```

```txt
comando: $env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
resultado: 92 passed, 1 warning.
evidencia: salida terminal.
```

```txt
comando: python -m ruff check apps\api scripts
resultado: All checks passed.
evidencia: salida terminal y runner slice 11.
```

```txt
comando: python -m compileall apps/api scripts
resultado: OK.
evidencia: salida terminal y runner slice 11.
```

```txt
comando: corepack pnpm --filter @nodo/web build
resultado: OK; Next.js 15.5.20 build compiled successfully.
evidencia: salida terminal y runner slice 11.
```

## Tests

- Tests ejecutados:
  - slice 00 runner: 6 checks OK.
  - slice 01 runner: 6 checks OK.
  - slice 02 runner: 3 checks OK.
  - slice 03 runner: 3 checks OK.
  - slice 04 runner: 3 checks OK.
  - slice 05 runner: 3 checks OK.
  - slice 06 runner: 3 checks OK.
  - slice 07 runner: 3 checks OK.
  - slice 08 runner: 3 checks OK.
  - slice 09 runner: 3 checks OK.
  - slice 10 runner: 4 checks OK.
  - slice 11 runner: 7 checks OK.
  - backend pytest acumulado: 92 passed, 1 warning.
  - frontend build: OK.
  - ruff: OK.
  - compileall: OK.
  - frontend secret/private scan: OK, hits `[]`.
- Tests no ejecutados:
  - Stress completo 25/50/100 y dataset contractual 100%.
  - Supabase real, Redis cloud, storage real, Stripe live, Telegram real y deploy.
- Razon de tests no ejecutados:
  - La fase autorizada fue local-only.
  - La PC local se uso con cap progresivo 5 negocios / 10 ordenes para evitar una corrida larga de 200 negocios / 10000 usuarios / 2000 ordenes en este turno.
  - Servicios reales/deploy estaban explicitamente prohibidos.

## Evidencia

- Archivos de evidencia:
  - `evidence/slice_runs/slice_11_hardening_deploy_evidence.md`
  - `evidence/slice_runs/slice_11_hardening_deploy_test_results.json`
  - `evidence/slice_runs/slice_11_local_infra_check.json`
  - `evidence/slice_runs/slice_11_local_migrations.json`
  - `evidence/slice_runs/slice_11_local_schema_validation.json`
  - `evidence/slice_runs/slice_11_local_rollback.json`
  - `evidence/slice_runs/slice_11_local_seed.json`
  - `evidence/slice_runs/slice_11_local_smoke.json`
  - `evidence/slice_runs/slice_11_local_stress.json`
- Resultados JSON/logs:
  - Todos los JSON anteriores quedaron generados.
- Capturas si aplica:
  - No aplica; la fase fue backend/local tooling/stress, no QA visual.

## Errores encontrados y fixes aplicados

- Docker daemon no estaba corriendo al primer intento.
  - Fix: iniciar Docker Desktop y reintentar compose.
- Smoke inicial uso razon de disputa no canonica.
  - Fix: usar `payment_mobile_not_received`.
- Stress detecto falsa bandera de idempotency duplicates por replay inmediatamente posterior.
  - Fix: separar `idempotency_duplicates` de `idempotency_replay_conflicts` y reintentar replay breve.
- Rollback drill fallo en `0009.down`, `0010.down` y `0006.down` por datos de slices posteriores incompatibles con constraints previas.
  - Fix: limpiar datos introducidos por cada slice antes de restaurar constraints antiguas.
- Runner slice 11 fallo al invocar `corepack` via `subprocess` en Windows.
  - Fix: usar `corepack.cmd` en Windows.

## Riesgos residuales

- Riesgo: no se ejecuto contra Supabase real, Redis cloud, storage real, Stripe live, Telegram real ni deploy.
  - Impacto: falta prueba de integraciones externas y configuracion real.
  - Cuando se retoma: fase deploy/hardening externo autorizada por owner.
- Riesgo: stress completo 100% no ejecutado.
  - Impacto: no hay evidencia local del dataset contractual maximo.
  - Cuando se retoma: maquina/entorno dedicado o ventana de stress extendida.
- Riesgo: warning Starlette/httpx en TestClient.
  - Impacto: ruido de testing aceptado temporalmente; no fallo funcional.
  - Cuando se retoma: hardening de dependencias/test client.
- Riesgo: `LocalFilePrivateStorage` no es storage productivo.
  - Impacto: solo sirve para hardening local; runtime sin opt-in mantiene storage unavailable.
  - Cuando se retoma: integracion de storage privado real autorizada.

## Auto-verificacion de Builder

- No toque scope prohibido.
- No cambie reglas de negocio.
- No cambie estados/enums sin contrato.
- No cambie disclaimers.
- No expuse secretos.
- No use rutas/endpoints no aprobados.
- No cree tablas fuera del contrato.
- No deje tests fallando.
- No declare `READY_FOR_REAL_USE`.
- No avance a otro slice.
- No use Supabase real.
- No use Redis cloud.
- No use Stripe real/live.
- No use Telegram real.
- No hice deploy.

## Estado final permitido

```txt
READY_FOR_OWNER_REVIEW
```
