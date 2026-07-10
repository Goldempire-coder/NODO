# OWNER VERIFICATION - slice_05_payment_instructions_reports

Fecha: 2026-07-04

Estado builder recibido:

```txt
READY_FOR_OWNER_REVIEW
```

Estado owner despues de auditoria:

```txt
OWNER_ACCEPTED_FOR_NEXT_SLICE
```

No se declara `READY_FOR_REAL_USE`.

## Alcance auditado

- Backend `orders` extendido para instrucciones de pago, evidencia y reporte.
- Migracion `0006_slice_05_payment_instructions_reports`.
- UI `R-07_PAYMENT_INSTRUCTIONS` y `R-08_REPORT_PAYMENT`.
- Runner y evidencia de slice 05.
- Contratos corregidos de `slice_05_payment_instructions_reports`.

## Resultado

El slice cumple el contrato principal:

- `GET /api/v1/orders/{id}/payment-instructions` revela instrucciones completas solo al remitente owner.
- Reveal requiere `waiting_payment` y orden no vencida.
- Reveal setea `payment_data_revealed_at` y `payment_data_revealed_by`.
- Reveal audita `payment_instructions_viewed`.
- Reveal no crea reporte ni cambia estado.
- `POST /api/v1/orders/{id}/payment-evidence` usa `file_assets`.
- No se crean `payment_evidence_files` ni `storage_objects`.
- Evidencia no expone `storage_path`.
- `POST /api/v1/orders/{id}/payment-report` cambia `waiting_payment -> payment_reported`.
- Reporte de pago crea `payment_reports.status = submitted`.
- Reporte de pago no consume creditos.
- Reporte de pago mantiene `ad.status = in_order`.
- Reporte de pago mantiene creditos bloqueados.
- Reporte de pago no confirma negocio, no entrega pago movil y no completa la orden.
- `R-09_ORDER_TRACKING_CHAT` queda fuera de slice 05.

## Hallazgo corregido por owner

Durante la auditoria se detecto un riesgo tecnico no cubierto por los tests originales:

```txt
pending_payment_report_id y proof_file_id entraban como strings libres y podian llegar a columnas UUID en Postgres.
```

Impacto:

- Un `pending_payment_report_id` invalido podia pasar por runtime in-memory y fallar en PostgreSQL real al insertar `file_assets.resource_id`.
- Un `proof_file_id` invalido podia llegar al repositorio antes de devolver error seguro.

Correccion aplicada:

- `apps/api/app/modules/orders/service.py`
  - agrega validacion UUID segura.
  - normaliza IDs antes de consultar o insertar.
  - devuelve `ORDER_NOT_FOUND`, `AD_NOT_FOUND` o `INVALID_PAYMENT_EVIDENCE` segun el contexto.
- `apps/api/tests/test_payment_instructions_reports.py`
  - agrega cobertura para `pending_payment_report_id` no UUID en upload de evidencia.

Esta correccion no cambia reglas de producto ni amplia scope funcional; evita fallos 500 en runtime PostgreSQL y mantiene errores seguros.

## Verificacion ejecutada por owner

```txt
python scripts\run_slice_05_tests.py
resultado: OK
```

```txt
corepack pnpm --filter @nodo/web build
resultado: OK
```

```txt
python scripts\run_slice_00_tests.py
resultado: 6 passed / 0 failed
```

```txt
python scripts\run_slice_01_tests.py
resultado: 6 passed / 0 failed
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
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
resultado: 51 passed, 1 warning
```

```txt
python -m ruff check apps\api scripts
resultado: OK
```

```txt
python -m compileall apps/api scripts
resultado: OK
```

```txt
rg -n "BOT_TOKEN|JWT_SECRET|JWT_REFRESH_SECRET|test-bot-token|test-access-secret|test-refresh-secret|owner@example\.com|storage_path|account_value|payment_instructions_snapshot|BEGIN PRIVATE KEY|AKIA[0-9A-Z]{16}" apps\web\src apps\web\.next
resultado: sin matches
```

## Riesgos residuales

- Migraciones reales contra PostgreSQL/Supabase siguen pendientes.
- Redis real sigue pendiente.
- Storage privado real sigue pendiente; runtime normal responde `STORAGE_UNAVAILABLE` hasta configurar adaptador real.
- Smoke manual dentro de Telegram real sigue pendiente.
- Warning Starlette/httpx sigue aceptado temporalmente.
- Compra/acreditacion real de creditos sigue para `slice_08_credits_referrals`.

## Scope no aceptado como construido

- No se acepta `READY_FOR_REAL_USE`.
- No se construyo slice 06.
- No se construyo confirmacion/rechazo del negocio.
- No se construyo entrega/pago movil.
- No se construyo chat.
- No se construyeron disputas.
- No se construyeron jobs masivos.
- No se consumieron creditos por reportar pago.

## Decision

```txt
slice_05_payment_instructions_reports = OWNER_ACCEPTED_FOR_NEXT_SLICE
```

