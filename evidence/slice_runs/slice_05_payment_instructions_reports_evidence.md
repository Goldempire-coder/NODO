# Evidence - slice_05_payment_instructions_reports

Fecha: 2026-07-04
Estado: READY_FOR_OWNER_REVIEW

No se declara READY_FOR_REAL_USE.

## Scope verificado

- Reveal controlado de instrucciones completas: `GET /api/v1/orders/{id}/payment-instructions`.
- Upload privado de evidencia de pago: `POST /api/v1/orders/{id}/payment-evidence`.
- Reporte de pago del remitter: `POST /api/v1/orders/{id}/payment-report`.
- UI gobernada: `R-07_PAYMENT_INSTRUCTIONS` y `R-08_REPORT_PAYMENT`.
- Migracion reversible: `0006_slice_05_payment_instructions_reports`.
- Tests focales y runner nuevo de slice 05.

## Evidencia de contratos criticos

### Reveal controlado

- Solo remitter owner autenticado puede revelar instrucciones completas.
- Requiere orden `waiting_payment` y no vencida.
- Setea `payment_data_revealed_at` y `payment_data_revealed_by`.
- Audita `payment_instructions_viewed`.
- No crea `payment_reports`.
- No cambia `orders.status`.
- No consume creditos.

Prueba: `apps/api/tests/test_payment_instructions_reports.py`

Resultado: incluido en `slice_05_payment_instructions_reports_test_results.json`, `7 passed`.

### Payment evidence

- Usa `file_assets`.
- No crea `payment_evidence_files`.
- No crea `storage_objects`.
- Requiere `Idempotency-Key`.
- Valida MIME permitido.
- Rechaza archivos mayores a 5 MB.
- Devuelve metadata publica y `pending_payment_report_id`.
- No expone `storage_path`.
- Audita `payment_evidence_uploaded`.

Prueba: `apps/api/tests/test_payment_instructions_reports.py`

Resultado: incluido en `slice_05_payment_instructions_reports_test_results.json`, `7 passed`.

### Payment report

- Requiere auth JWT.
- Requiere `Idempotency-Key`.
- Solo permite remitter owner.
- Requiere orden `waiting_payment` no vencida.
- Valida metodo contra `payment_method_snapshot`.
- Crea `payment_reports.status = submitted`.
- Cambia `waiting_payment -> payment_reported`.
- Setea `paid_reported_at`, `business_response_warning_at` y `business_response_deadline_at`.
- Crea `order_state_events`.
- Audita `payment_reported`.
- Mantiene `ad.status = in_order`.
- Mantiene creditos bloqueados.
- No consume creditos.
- No confirma recepcion del negocio.
- No entrega pago movil.
- No completa la orden.

Prueba: `apps/api/tests/test_payment_instructions_reports.py`

Resultado: incluido en `slice_05_payment_instructions_reports_test_results.json`, `7 passed`.

### Idempotencia

- Retry con la misma `Idempotency-Key` y mismo payload devuelve el mismo resultado.
- Misma `Idempotency-Key` con payload distinto devuelve conflicto seguro.
- No se creo tabla `idempotency_keys`; se usa el contrato de `payment_reports`.

Prueba: `apps/api/tests/test_payment_instructions_reports.py`

Resultado: incluido en `slice_05_payment_instructions_reports_test_results.json`, `7 passed`.

### Secret/private-data scan frontend

Comando equivalente ejecutado por runner:

```txt
frontend secret/private-data scan
```

Resultado:

```json
{
  "exit_code": 0,
  "hits": []
}
```

No se detectaron secretos, `storage_path`, instrucciones privadas ni identificadores sensibles prohibidos en source/build frontend.

## Comandos ejecutados

```txt
python -m pip install "python-multipart>=0.0.20,<1.0.0"
resultado: OK, python-multipart 0.0.32 instalado
motivo: FastAPI requiere parser multipart para upload de evidencia
registro: apps/api/requirements.txt
```

```txt
$env:PYTHONPATH='apps/api'; python -m pytest apps/api/tests/test_payment_instructions_reports.py -q
resultado: 7 passed, 1 warning
```

```txt
$env:PYTHONPATH='apps/api'; python -m pytest apps/api/tests -q
resultado: 51 passed, 1 warning
```

```txt
python -m ruff check apps/api scripts
resultado: All checks passed!
```

```txt
python -m compileall apps/api scripts
resultado: OK
```

```txt
corepack pnpm --filter @nodo/web build
resultado: OK
```

```txt
python scripts\run_slice_00_tests.py
resultado: OK, 6 passed
```

```txt
python scripts\run_slice_01_tests.py
resultado: OK, 6 passed
```

```txt
python scripts\run_slice_02_tests.py
resultado: OK
```

```txt
python scripts\run_slice_03_tests.py
resultado: OK
```

```txt
python scripts\run_slice_04_tests.py
resultado: OK
```

```txt
python scripts\run_slice_05_tests.py
resultado: OK, 7 passed, 1 warning; compileall OK; frontend scan sin hits
```

```txt
rg -n "BOT_TOKEN|JWT_SECRET|JWT_REFRESH_SECRET|test-bot-token|test-access-secret|test-refresh-secret|owner@example\.com|storage_path|account_value|payment_instructions_snapshot|BEGIN PRIVATE KEY|AKIA[0-9A-Z]{16}" apps/web/src apps/web/.next
resultado: exit 1, sin matches
```

## Evidencia JSON

- `evidence/slice_runs/slice_05_payment_instructions_reports_test_results.json`

Resultado principal:

```txt
slice: slice_05_payment_instructions_reports
pytest focal: 7 passed, 1 warning
compileall: OK
frontend secret/private-data scan: OK, hits []
```

## Riesgos residuales heredados

- Migraciones reales contra PostgreSQL/Supabase siguen pendientes hasta tener servicio/credenciales.
- Redis real sigue pendiente.
- Storage privado real sigue pendiente; runtime normal responde error seguro si no hay storage configurado.
- Smoke manual Telegram real sigue pendiente.
- Warning Starlette/httpx aceptado temporalmente.
- Compra/acreditacion real de creditos queda fuera de este slice.

## Scope no construido

- Confirmacion/rechazo del negocio.
- Entrega/pago movil.
- Chat.
- Disputas.
- Jobs masivos.
- Consumo de creditos.
- Slice 06.

## Estado final

READY_FOR_OWNER_REVIEW
