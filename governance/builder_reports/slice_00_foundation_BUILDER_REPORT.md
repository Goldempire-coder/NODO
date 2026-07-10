# BUILDER_REPORT - slice_00_foundation

## Slice

slice_00_foundation

## Estado final

READY_FOR_OWNER_REVIEW

## Scope construido

- Repo/tooling base.
- `apps/web` con Next.js, TypeScript, Tailwind y Telegram SDK/UI kit instalado.
- `apps/api` con FastAPI, estructura modular, env validation, health/ready/version, logging seguro, error contract, security headers y CORS.
- Conexion base DB/Redis con clientes `psycopg`/`redis` cuando estan instalados y fallback seguro por socket.
- Migraciones base para `users`, `audit_logs`, `job_runs`, `app_metadata`.
- Tests minimos y evidencia en `evidence/slice_runs/`.

## Archivos creados/modificados y lineas relevantes

- `package.json`: 1-15, scripts workspace y test.
- `pnpm-workspace.yaml`: 1-2, workspace apps.
- `pnpm-lock.yaml`: 1-1851, lockfile frontend.
- `.env.example`: 1-15, plantilla sin secretos reales.
- `apps/web/package.json`: 1-27, Next/React/Tailwind/Telegram deps.
- `apps/web/next.config.mjs`: 1-7, Next config.
- `apps/web/postcss.config.mjs`: 1-8, Tailwind/PostCSS.
- `apps/web/tailwind.config.ts`: 1-23, tokens base NODO.
- `apps/web/tsconfig.json`: 1-20, TypeScript strict.
- `apps/web/src/app/globals.css`: 1-21, base visual tecnica.
- `apps/web/src/app/layout.tsx`: 1-15, layout minimo.
- `apps/web/src/app/page.tsx`: 1-29, pantalla tecnica neutral, no landing comercial.
- `apps/web/src/lib/env.ts`: 1-21, public env helper.
- `apps/api/requirements.txt`: 1-12, dependencias Python aprobadas.
- `apps/api/app/main.py`: 1-44, FastAPI app, middleware, router, safe handler.
- `apps/api/app/core/config.py`: 1-72, env validation y redaction helper.
- `apps/api/app/core/errors.py`: 1-26, error contract base.
- `apps/api/app/core/logging.py`: 1-46, logging seguro con redaction.
- `apps/api/app/core/network.py`: 1-25, connectivity checks.
- `apps/api/app/repositories/database.py`: 1-19, DB connectivity repository con `psycopg` y fallback.
- `apps/api/app/repositories/redis.py`: 1-20, Redis connectivity repository con `redis` client y fallback.
- `apps/api/app/services/health_service.py`: 1-39, health/version/readiness service.
- `apps/api/app/routes/health.py`: 1-33, `/health`, `/ready`, `/version`.
- `apps/api/app/shared/audit/events.py`: 1-5, audit events foundation.
- `apps/api/app/shared/security/headers.py`: 1-13, security headers middleware.
- `apps/api/tests/test_foundation_http.py`: 1-50, FastAPI HTTP tests.
- `database/migrations/0001_slice_00_foundation.up.sql`: 1-100, base schema/indexes/triggers.
- `database/migrations/0001_slice_00_foundation.down.sql`: 1-7, rollback.
- `scripts/run_slice_00_tests.py`: 1-145, contract runner.
- `evidence/slice_runs/slice_00_foundation_test_results.json`: 1-28, machine-readable test evidence.
- `evidence/slice_runs/slice_00_foundation_evidence.md`: 1-96, human-readable evidence.
- `governance/builder_reports/slice_00_foundation_BUILDER_REPORT.md`: 1-end, final report.

## Contratos cumplidos

- `CODE_ARCHITECTURE_MASTER.md`: separa routes, services, repositories, core, shared security/audit y tests.
- `DATA_CONTRACT.md`: crea solo `users`, `audit_logs`, `job_runs`, `app_metadata`.
- `DATABASE_CONSTRAINTS.md`: uuid PK, timestamps, checks, indexes, append-only audit logs.
- `INDEXES.md`: indices para users, audit_logs, job_runs y app_metadata.
- `SECURITY_MASTER.md`: secrets fuera de repo/frontend/logs, security headers, CORS base, logging seguro.
- `AUDIT_LOG_POLICY.md`: audit logs usan `resource_type/resource_id`, `request_id` obligatorio, `job_id` opcional.
- `API_OVERVIEW.md`: FastAPI autoridad backend, `/api/v1`, safe errors.
- `ERROR_CONTRACT.md`: payload `{ error, request_id }`.
- `SLICE_CONTRACTS_MASTER.md`: slice 00 sin features de producto.
- `TELEGRAM_MINI_APP_RULES.md`: Telegram SDK/UI kit instalado para slices futuros; no pantallas finales construidas.

## Dependencias instaladas

Frontend, registradas en `apps/web/package.json` y `pnpm-lock.yaml`:

- `@telegram-apps/sdk` 3.11.8: SDK Telegram Mini App para slices futuros.
- `@telegram-apps/telegram-ui` 2.1.13: UI kit Telegram para slices futuros.
- `next` 15.5.20: frontend aprobado.
- `react` 18.2.0: runtime UI compatible con telegram-ui.
- `react-dom` 18.2.0: runtime DOM compatible con telegram-ui.
- `typescript` 5.9.3: TypeScript frontend.
- `tailwindcss` 3.4.19, `postcss` 8.5.16, `autoprefixer` 10.5.2: Tailwind build chain.
- `@types/node` 22.20.0, `@types/react` 18.3.31, `@types/react-dom` 18.3.7: types.

Backend/dev, registradas en `apps/api/requirements.txt`:

- `fastapi` 0.136.3: API framework.
- `uvicorn` 0.49.0: ASGI runtime.
- `pydantic` 2.13.4: validation dependency.
- `pydantic-settings` 2.14.2: approved settings dependency for upcoming config hardening.
- `sqlalchemy` 2.0.51: approved DB toolkit.
- `alembic` 1.18.5: approved migration tooling.
- `psycopg` 3.3.4: PostgreSQL/Supabase driver.
- `redis` 8.0.0: Redis client.
- `pytest` 9.0.2 and `httpx` 0.28.1: API tests.
- `ruff` 0.15.20 and `mypy` 2.1.0: quality tooling.

## Comandos ejecutados

- `python -m pip install -r apps\api\requirements.txt pytest httpx pydantic pydantic-settings sqlalchemy alembic psycopg[binary] redis ruff mypy`: paso con permisos de red.
- `corepack pnpm install`: paso.
- `corepack pnpm --filter @nodo/web build`: paso.
- `python -m compileall apps scripts`: paso.
- `python scripts\run_slice_00_tests.py`: paso, 6 passed / 0 failed.
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: paso, 3 passed / 1 warning.
- `python -m ruff check apps\api scripts`: paso.
- `corepack pnpm --filter @nodo/web list --depth 0`: paso.
- `python -m pip show ...`: paso.

## Resultados de tests

- Contract runner: 6 passed, 0 failed.
- FastAPI HTTP tests: 3 passed, 1 warning.
- Python compileall: passed.
- Ruff: passed.
- Next production build: passed.

## Tests no ejecutados y razon

- PostgreSQL/Supabase migration up/down real: no live DATABASE_URL service/credentials were provided for this run.
- Redis ready success path: no live REDIS_URL service was provided for this run.
- mypy: installed and recorded, but no mypy config is part of slice 00 yet.

## Evidencia creada

- `evidence/slice_runs/slice_00_foundation_test_results.json`
- `evidence/slice_runs/slice_00_foundation_evidence.md`

## Riesgos residuales

- Ejecutar migraciones contra Supabase/PostgreSQL real cuando existan credenciales de staging/local.
- Ejecutar readiness success contra Redis real cuando exista servicio local/staging.
- La advertencia de FastAPI TestClient sobre `httpx` es de dependencia; no rompe el test.

## Que NO toque

- No construi onboarding.
- No construi marketplace.
- No construi ordenes reales.
- No construi pagos.
- No construi creditos reales.
- No construi admin completo.
- No construi pantallas finales.
- No cambie reglas de negocio.
- No cambie estados/enums del control plane.
- No cambie disclaimers.
- No cree tablas fuera de `users`, `audit_logs`, `job_runs`, `app_metadata`.
- No use `entity_type/entity_id`.
- No use `business` como rol persistente.
- No use `guest` como rol persistente.
- No declare READY_FOR_REAL_USE.
