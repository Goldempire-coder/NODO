# OWNER VERIFICATION - slice_04_order_creation

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

- Backend `orders`: routes, schemas, service, repository, policy, state machine.
- Migracion `0005_slice_04_order_creation`.
- UI `R-05_CREATE_ORDER`, `R-06_ORDER_SUMMARY`, `R-12_MY_ORDERS`.
- Runner y evidencia de slice 04.
- Contratos corregidos de `slice_04_order_creation`.

## Resultado

El slice cumple el contrato principal:

- `POST /api/v1/orders` persiste `waiting_payment`.
- Crear orden mueve anuncio `active -> in_order`.
- Crear orden no consume creditos.
- Crear orden no cobra al usuario.
- Crear orden no reporta pago.
- Crear orden no revela instrucciones completas.
- Detail/list solo exponen instrucciones masked/resumen.
- Idempotencia de create usa `orders.idempotency_key`.
- Cancel/extend quedan limitados a `waiting_payment`.
- Expiracion pasiva materializa `cancelled/payment_not_reported_in_time`.
- `R-07_PAYMENT_INSTRUCTIONS` queda para slice 05.
- `B-11_INCOMING_ORDERS` queda para slice 06.

## Hallazgo corregido por owner

Durante la auditoria se detecto un riesgo tecnico no cubierto por tests en memoria:

```txt
Postgres repositories passed Python dict directly into jsonb columns.
```

Impacto:

- En runtime Postgres real, `payment_instructions_snapshot`, `receiver_data_json`, `metadata_json` o `submitted_data_json` podian fallar por adaptacion JSON.
- El problema no se detectaba con `APP_ENV=test` porque usa repositorios in-memory.

Correccion aplicada:

- `apps/api/app/modules/orders/repository.py`
  - `payment_instructions_snapshot` usa `Jsonb`.
  - `receiver_data_json` usa `Jsonb`.
  - `order_state_events.metadata_json` usa `Jsonb`.
- `apps/api/app/shared/audit/audit_service.py`
  - `audit_logs.metadata_json` usa `Jsonb`.
  - Serializacion usa `json.dumps(..., default=str)` para soportar `Decimal` y timestamps en metadata.
- `apps/api/app/modules/businesses/repository.py`
  - `business_verification_submissions.submitted_data_json` usa `Jsonb`.

Esta correccion no cambia reglas de producto ni amplia scope funcional; reduce riesgo de fallo en runtime PostgreSQL.

## Verificacion ejecutada por owner

```txt
python scripts\run_slice_04_tests.py
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
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
resultado: 44 passed, 1 warning
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
- Storage privado real sigue pendiente.
- Smoke manual dentro de Telegram real sigue pendiente.
- Warning Starlette/httpx sigue aceptado temporalmente.
- Compra/acreditacion real de creditos sigue para `slice_08_credits_referrals`.

## Scope no aceptado como construido

- No se acepta `READY_FOR_REAL_USE`.
- No se construyo slice 05.
- No se construyo reporte de pago.
- No se construyo revelado completo de instrucciones.
- No se construyo confirmacion de negocio.
- No se construyo delivery/pago movil.
- No se construyo chat.
- No se construyeron disputas.
- No se construyeron jobs masivos.

## Decision

```txt
slice_04_order_creation = OWNER_ACCEPTED_FOR_NEXT_SLICE
```

