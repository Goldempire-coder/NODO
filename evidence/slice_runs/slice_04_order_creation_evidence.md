# slice_04_order_creation evidence

Fecha: 2026-07-04

Estado tecnico reportado por Builder:

```txt
READY_FOR_OWNER_REVIEW
```

No se declara `READY_FOR_REAL_USE`.

## Alcance construido

- Backend modular `orders` con `routes`, `schemas`, `service`, `repository`, `policy`, `state_machine` y tests.
- Endpoints:
  - `POST /api/v1/orders`
  - `GET /api/v1/orders/{id}`
  - `GET /api/v1/orders/mine`
  - `POST /api/v1/orders/{id}/extend-payment-deadline`
  - `POST /api/v1/orders/{id}/cancel`
- Migracion reversible `0005_slice_04_order_creation` para:
  - `orders`
  - `order_state_events`
  - FK `credits_ledger.related_order_id -> orders(id)`
  - indices de busqueda, deadline, public code e idempotencia parcial.
- Frontend scope:
  - `R-05_CREATE_ORDER`
  - `R-06_ORDER_SUMMARY`
  - `R-12_MY_ORDERS`
- Runner:
  - `scripts/run_slice_04_tests.py`

## Evidencia de reglas criticas

- `create_order` persiste `waiting_payment`, guarda snapshot privado, mueve ad a `in_order`, escribe `order_state_events`, audita `order_created` y `ad_moved_in_order`.
- Runtime Postgres mueve `ads.status = in_order` e inserta `orders` en una misma transaccion dentro de `PostgresOrderRepository.create_order`.
- Idempotencia de create usa `orders.idempotency_key` y no crea tabla separada.
- Misma key + mismo payload devuelve la misma orden; misma key + payload distinto devuelve `IDEMPOTENCY_PAYLOAD_MISMATCH`.
- Create/detail/list no devuelven `account_value` ni instrucciones completas.
- `payment_instructions_snapshot` se persiste solo en backend privado.
- `create_order` no consume creditos; cancel/expiration libera hold si aplica.
- `waiting_payment` vencida se materializa pasivamente a `cancelled` con `payment_not_reported_in_time`.

## Comandos ejecutados

```txt
corepack pnpm --filter @nodo/web build
Resultado: OK
```

```txt
python scripts\run_slice_00_tests.py
Resultado: 6 passed / 0 failed
```

```txt
python scripts\run_slice_01_tests.py
Resultado: 6 passed / 0 failed
```

```txt
python scripts\run_slice_02_tests.py
Resultado: OK
```

```txt
python scripts\run_slice_03_tests.py
Resultado: OK
```

```txt
python scripts\run_slice_04_tests.py
Resultado: OK
Evidencia JSON: evidence/slice_runs/slice_04_order_creation_test_results.json
```

```txt
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
Resultado: 44 passed, 1 warning
Warning: Starlette/httpx TestClient warning aceptado temporalmente por owner.
```

```txt
python -m ruff check apps\api scripts
Resultado: All checks passed
```

```txt
python -m compileall apps/api scripts
Resultado: OK
```

```txt
rg -n "BOT_TOKEN|JWT_SECRET|JWT_REFRESH_SECRET|test-bot-token|test-access-secret|test-refresh-secret|owner@example\.com|storage_path|account_value|payment_instructions_snapshot|BEGIN PRIVATE KEY|AKIA[0-9A-Z]{16}" apps\web\src apps\web\.next
Resultado: sin matches; exit code 1 de ripgrep significa no matches.
```

## Tests cubiertos

- create order success.
- create order persiste `waiting_payment`.
- create order mueve ad `active -> in_order`.
- create order no consume creditos.
- create order guarda snapshot inmutable privado.
- create/detail/list no revelan instrucciones completas ni `account_value`.
- ad inactive/paused falla.
- negocio no approved falla.
- amount out of range falla.
- `Idempotency-Key` requerido.
- misma idempotency key + mismo payload devuelve misma orden.
- misma idempotency key + payload distinto falla seguro.
- detail own order OK.
- detail other user no filtra existencia.
- mine solo devuelve ordenes propias.
- cancel `waiting_payment` libera anuncio/creditos.
- cancel despues de `paid_reported_at` prohibido.
- extend una sola vez.
- waiting_payment vencida se materializa pasivamente.
- audit events y state events.
- migracion 0005 contiene tablas/constraints/indices requeridos.
- frontend build.
- backend pytest acumulado.
- ruff.
- compileall.
- secret/private-data scan frontend.

## Riesgos residuales

- Migraciones reales contra PostgreSQL/Supabase siguen pendientes hasta tener servicio/credenciales.
- Redis real sigue pendiente.
- Storage privado real sigue pendiente por hardening/deploy.
- Smoke manual dentro de Telegram real no ejecutado.
- Warning Starlette/httpx TestClient sigue aceptado temporalmente.
- No existe flujo real de compra/acreditacion de creditos hasta `slice_08_credits_referrals`; se mantiene el comportamiento de holds existentes de slice 03.

## Scope no construido

- No se construyo `slice_05`.
- No se construyo reporte de pago.
- No se revelaron instrucciones completas de pago.
- No se construyo confirmacion de negocio.
- No se construyo entrega/pago movil.
- No se construyo chat.
- No se construyeron disputas.
- No se construyeron jobs masivos.
- No se declaro `READY_FOR_REAL_USE`.

## Estado final

```txt
READY_FOR_OWNER_REVIEW
```
