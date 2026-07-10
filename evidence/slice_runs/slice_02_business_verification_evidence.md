# slice_02_business_verification evidence

Fecha: 2026-07-04
Estado: READY_FOR_OWNER_REVIEW

## Evidencia tecnica

- Backend business verification implementado en `apps/api/app/modules/businesses/`.
- Endpoints autorizados registrados bajo `/api/v1`.
- Migracion reversible creada:
  - `database/migrations/0003_slice_02_business_verification.up.sql`
  - `database/migrations/0003_slice_02_business_verification.down.sql`
- UI minima gobernada integrada en `apps/web/src/app/page.tsx`.
- Resultados JSON generados en `evidence/slice_runs/slice_02_business_verification_test_results.json`.

## Comandos ejecutados

```txt
python -m pip install --user -r apps\api\requirements.txt
resultado: OK, requirements already satisfied; no dependency was newly recorded in repo.
```

```txt
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_business_verification.py -q
resultado: 9 passed, 1 Starlette/httpx warning.
```

```txt
python scripts\run_slice_02_tests.py
resultado: OK; JSON evidence regenerated.
```

```txt
corepack pnpm --filter @nodo/web build
resultado: OK; Next.js compiled and type-checked.
```

```txt
python scripts\run_slice_00_tests.py
resultado: passed 6, failed 0.
```

```txt
python scripts\run_slice_01_tests.py
resultado: passed 6, failed 0.
```

```txt
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
resultado: 24 passed, 1 Starlette/httpx warning.
```

```txt
python -m ruff check apps\api scripts
resultado: All checks passed.
```

```txt
python -m compileall apps/api scripts
resultado: OK.
```

```txt
rg -n "BOT_TOKEN|JWT_SECRET|JWT_REFRESH_SECRET|test-bot-token|test-access-secret|test-refresh-secret|storage_path|refresh_token" apps\web\src apps\web\.next
resultado: no matches.
```

## Contratos verificados

- `business.verification_status` persistente solo usa `pending`, `approved`, `rejected`, `suspended`, `blocked`.
- `draft` queda como texto UI/workflow, no estado persistente.
- `under_review` no fue usado como `verification_status`.
- Uploads privados usan `file_assets`; `storage_path` no se expone en responses ni frontend.
- Signed URL se genera solo para admin/super_admin con reason y audit; no se persiste.
- Support puede ver lista/detalle segun contrato, pero no approve/reject ni view-url.
- Owner solo opera sobre negocio propio.
- Idempotencia aplicada a create/update/submit/approve/reject.
- Rate limit aplicado a endpoints sensibles con Redis en runtime normal e in-memory solo en test.
- Audit events implementados: `business_created`, `business_updated`, `business_submitted`, `business_approved`, `business_rejected`, `payment_method_added`, `verification_document_uploaded`, `verification_document_viewed`.

## Riesgos residuales

- Migraciones reales contra PostgreSQL/Supabase siguen pendientes hasta contar con servicio/credenciales.
- Readiness success contra Redis real sigue pendiente hasta contar con servicio/credenciales.
- Storage real privado no esta configurado en runtime normal; el adapter runtime responde `STORAGE_UNAVAILABLE` de forma segura.
- Warning Starlette/httpx en TestClient se mantiene como riesgo aceptado temporalmente.
- Smoke manual dentro de Telegram real no ejecutado en esta corrida.

## Estado

READY_FOR_OWNER_REVIEW
