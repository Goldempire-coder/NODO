# slice_00_foundation evidence

Date: 2026-07-03
State: READY_FOR_OWNER_REVIEW

## Commands executed

```txt
python -m compileall apps scripts
Result: passed
```

```txt
python scripts\run_slice_00_tests.py
Result: passed, 6 passed, 0 failed
Evidence JSON: evidence/slice_runs/slice_00_foundation_test_results.json
```

```txt
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
Result: passed, 3 passed, 1 warning
Warning: FastAPI TestClient emits StarletteDeprecationWarning about httpx.
```

```txt
python -m ruff check apps\api scripts
Result: passed
```

```txt
corepack pnpm install
Result: passed
```

```txt
corepack pnpm --filter @nodo/web build
Result: passed
Next.js: 15.5.20
Output: route / static, first load JS 102 kB
```

```txt
corepack pnpm --filter @nodo/web list --depth 0
Result: passed
```

```txt
python -m pip show fastapi uvicorn pydantic pydantic-settings sqlalchemy alembic psycopg redis pytest httpx ruff mypy
Result: passed
```

## Dependency versions recorded

Frontend dependencies in `apps/web/package.json` and `pnpm-lock.yaml`:

- @telegram-apps/sdk 3.11.8
- @telegram-apps/telegram-ui 2.1.13
- next 15.5.20
- react 18.2.0
- react-dom 18.2.0
- typescript 5.9.3
- tailwindcss 3.4.19
- postcss 8.5.16
- autoprefixer 10.5.2
- @types/node 22.20.0
- @types/react 18.3.31
- @types/react-dom 18.3.7

Backend/dev dependencies in `apps/api/requirements.txt`:

- fastapi 0.136.3
- uvicorn 0.49.0
- pydantic 2.13.4
- pydantic-settings 2.14.2
- SQLAlchemy 2.0.51
- alembic 1.18.5
- psycopg 3.3.4
- redis 8.0.0
- pytest 9.0.2
- httpx 0.28.1
- ruff 0.15.20
- mypy 2.1.0

## Tests covered

- env validation
- health response
- version response
- ready response when DB/Redis unavailable
- DB unavailable
- Redis unavailable
- migration contract for users, audit_logs, job_runs, app_metadata
- audit_logs resource_type/resource_id, request_id, optional job_id
- persistent roles include business_owner and super_admin
- persistent roles exclude business and guest
- audit log append-only trigger exists
- no backend secret names in frontend source bundle inputs
- safe logging redaction
- FastAPI health/version/ready HTTP contract
- Next.js production build
- Python lint with ruff

## Tests not executed

- Real PostgreSQL migration up/down was not executed because no live DATABASE_URL service was provided in this slice run.
- Real Redis success readiness was not executed because no live REDIS_URL service was provided in this slice run.
- mypy was installed and recorded but not executed; no mypy config is part of slice_00_foundation yet.

## Residual risks

- Live Supabase/PostgreSQL and Redis smoke should be run when environment credentials/services are provided.
- FastAPI TestClient warning is dependency-level and does not fail the test suite.
