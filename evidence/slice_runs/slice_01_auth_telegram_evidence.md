# slice_01_auth_telegram Evidence

Fecha: 2026-07-03

Estado previo aceptado por owner:

- `slice_00_foundation = READY_FOR_OWNER_REVIEW`
- No `READY_FOR_REAL_USE`

Riesgo residual heredado mantenido:

- Migraciones no ejecutadas contra PostgreSQL/Supabase real.
- Readiness success no ejecutado contra Redis real.

## Comandos ejecutados

```powershell
python -m compileall apps/api scripts
```

Resultado: passed.

```powershell
python scripts\run_slice_01_tests.py
```

Resultado: 6 passed, 0 failed.
Salida: `evidence/slice_runs/slice_01_auth_telegram_test_results.json`.

```powershell
python scripts\run_slice_00_tests.py
```

Resultado: 6 passed, 0 failed.

```powershell
python -m ruff check apps\api scripts
```

Resultado: All checks passed.

```powershell
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
```

Resultado: 13 passed, 1 warning.
Warning: Starlette/TestClient deprecation from installed FastAPI/TestClient stack.

```powershell
corepack pnpm --filter @nodo/web build
```

Resultado: Next.js build passed.
Warning: Tailwind no utility classes detected because this slice uses local CSS for the technical auth entry.

```powershell
rg -n "BOT_TOKEN|JWT_SECRET|JWT_REFRESH_SECRET|DATABASE_URL|REDIS_URL|SUPABASE_SERVICE_ROLE_KEY|123456:test-bot-token|test-access-secret|test-refresh-secret" apps/web/.next
```

Resultado: sin matches.

## Evidencia creada

- `evidence/slice_runs/slice_01_auth_telegram_test_results.json`
- `evidence/slice_runs/slice_01_auth_telegram_evidence.md`

