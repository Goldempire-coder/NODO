# BUILDER REPORT - slice_04_order_creation

## Slice

- Slice: `slice_04_order_creation`
- Estado final: `READY_FOR_OWNER_REVIEW`
- Fecha: 2026-07-04
- Builder/agente: Codex

No se declara `READY_FOR_REAL_USE`.

## Scope construido

- Incluido:
  - Modulo backend `orders`.
  - Endpoints canonicos de ordenes.
  - Migracion reversible `0005_slice_04_order_creation`.
  - UI minima gobernada para `R-05_CREATE_ORDER`, `R-06_ORDER_SUMMARY`, `R-12_MY_ORDERS`.
  - Tests y runner de slice 04.
  - Evidencia en `evidence/slice_runs/`.
- Excluido:
  - `slice_05_payment_instructions_reports`.
  - Reporte de pago.
  - Full payment instructions reveal.
  - Confirmacion de negocio.
  - Entrega/pago movil.
  - Chat/disputas/jobs masivos.
- Que NO toque:
  - Reglas de negocio de creditos fuera de release en cancel/expiration.
  - Estados/enums sin contrato.
  - Disclaimers fuera del texto requerido.
  - Rutas legacy `/orders`.

## Archivos y lineas

```txt
apps/api/app/modules/orders/models.py
lineas: 17-87
motivo: modelos internos para orders y order_state_events.
contrato cumplido: DATA_CONTRACT orders/order_state_events.
```

```txt
apps/api/app/modules/orders/schemas.py
lineas: 8-22
motivo: payloads de create/cancel/extend.
contrato cumplido: ORDERS_API y slice API_CONTRACT.
```

```txt
apps/api/app/modules/orders/policy.py
lineas: 8-15
motivo: RBAC remitter y ownership.
contrato cumplido: SECURITY_CONTRACT ownership/RBAC.
```

```txt
apps/api/app/modules/orders/state_machine.py
lineas: 17-42
motivo: expiracion waiting_payment, extend once, cancel allowed.
contrato cumplido: STATE_CONTRACT.
```

```txt
apps/api/app/modules/orders/repository.py
lineas: 60-135, 139-284
motivo: repositorio in-memory/test y Postgres; create Postgres mueve ad a in_order e inserta order en una transaccion.
contrato cumplido: arquitectura modular, atomic create, idempotency via orders.idempotency_key, state events.
```

```txt
apps/api/app/modules/orders/service.py
lineas: 18-330
motivo: reglas de create/detail/mine/extend/cancel/expiration, snapshots privados, audit y masked response.
contrato cumplido: API, security, state, audit, sensitive data.
```

```txt
apps/api/app/modules/orders/routes.py
lineas: 29-82
motivo: endpoints canonicos autorizados.
contrato cumplido: ORDERS_API.
```

```txt
apps/api/app/main.py
lineas: 12-13, 43, 52, 70
motivo: registrar repositorio y router de orders.
contrato cumplido: arquitectura modular y endpoints slice 04.
```

```txt
apps/api/app/core/errors.py
lineas: 42-50
motivo: codigos de error canonicos de ordenes.
contrato cumplido: ERROR_CONTRACT.
```

```txt
database/migrations/0005_slice_04_order_creation.up.sql
lineas: 1-117
motivo: crear orders, order_state_events, constraints, FK e indices.
contrato cumplido: DATA_CONTRACT, DATABASE_CONSTRAINTS, INDEXES.
```

```txt
database/migrations/0005_slice_04_order_creation.down.sql
lineas: 1-16
motivo: rollback reversible del slice.
contrato cumplido: migration reversibility.
```

```txt
apps/api/tests/test_order_creation.py
lineas: 154-371
motivo: pruebas obligatorias del slice 04.
contrato cumplido: QA.md y SECURITY_TESTS aplicables.
```

```txt
scripts/run_slice_04_tests.py
lineas: 14-70
motivo: runner y evidencia JSON del slice.
contrato cumplido: evidencia obligatoria.
```

```txt
apps/web/src/app/page.tsx
lineas: 14-17, 132-168, 313-321, 455-550, 667, 795-824, 990-1089
motivo: UI de create order, order summary y my orders con masking/disclaimer.
contrato cumplido: UI_CONTRACT, TELEGRAM Mini App rules, sensitive display.
```

## Dependencias

No se instalaron ni modificaron dependencias.

## Endpoints construidos

- `POST /api/v1/orders`
- `GET /api/v1/orders/{id}`
- `GET /api/v1/orders/mine`
- `POST /api/v1/orders/{id}/extend-payment-deadline`
- `POST /api/v1/orders/{id}/cancel`

No se crearon rutas legacy `/orders` fuera del prefijo `/api/v1`.

## Migraciones creadas

- `database/migrations/0005_slice_04_order_creation.up.sql`
- `database/migrations/0005_slice_04_order_creation.down.sql`

## Contratos cumplidos

- Governance:
  - Construido solo `slice_04_order_creation`.
  - No avance a slice 05.
  - No `READY_FOR_REAL_USE`.
- Data:
  - `orders`, `order_state_events`, FK/indices/constraints.
  - `orders.idempotency_key` sin tabla `idempotency_keys`.
- API:
  - Endpoints canonicos y errores seguros.
  - Create devuelve `waiting_payment`.
  - Detail/list masked.
- Security:
  - Auth JWT requerida por dependency existente.
  - RBAC remitter/ownership.
  - Rate limit por accion.
  - Idempotency en mutaciones.
  - No full instructions/account values en responses/logs.
- UI/UX:
  - R-05, R-06, R-12 en Mini App existente.
  - Loading/error/empty/success/forbidden via estados existentes y mensajes seguros.
  - MainButton para create order.
  - Disclaimer requerido.
- QA:
  - Runner slice 04.
  - Pytest acumulado.
  - Build frontend.
  - Ruff, compileall, secret scan.

## Comandos ejecutados

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
evidencia: evidence/slice_runs/slice_04_order_creation_test_results.json
```

```txt
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
resultado: 44 passed, 1 warning
```

```txt
python -m ruff check apps\api scripts
resultado: All checks passed
```

```txt
python -m compileall apps/api scripts
resultado: OK
```

```txt
rg -n "BOT_TOKEN|JWT_SECRET|JWT_REFRESH_SECRET|test-bot-token|test-access-secret|test-refresh-secret|owner@example\.com|storage_path|account_value|payment_instructions_snapshot|BEGIN PRIVATE KEY|AKIA[0-9A-Z]{16}" apps\web\src apps\web\.next
resultado: sin matches
```

## Tests

- Tests ejecutados:
  - `apps/api/tests/test_order_creation.py`: 9 passed, 1 warning.
  - Pytest acumulado: 44 passed, 1 warning.
  - Slice runners 00, 01, 02, 03, 04.
  - Frontend build.
  - Ruff.
  - Compileall.
  - Secret/private-data scan frontend source/build.
- Tests no ejecutados:
  - Migraciones reales contra PostgreSQL/Supabase.
  - Redis real.
  - Smoke manual Telegram real.
- Razon de tests no ejecutados:
  - Servicios/credenciales reales no disponibles; riesgo residual heredado aceptado temporalmente por owner.

## Evidencia

- `evidence/slice_runs/slice_04_order_creation_evidence.md`
- `evidence/slice_runs/slice_04_order_creation_test_results.json`

## Evidencia especifica

- No se revelan instrucciones completas:
  - Tests verifican que responses detail/list/create no contienen `owner@example.com` ni `account_value`.
  - Secret scan frontend source/build sin matches para `account_value` ni `payment_instructions_snapshot`.
- `create_order` no consume creditos:
  - Test compara wallet antes/despues de create y conserva available/blocked.
- Idempotencia:
  - Test confirma misma key + mismo payload devuelve misma orden.
  - Test confirma misma key + payload distinto devuelve `IDEMPOTENCY_PAYLOAD_MISMATCH`.

## Riesgos residuales

- Riesgo: migraciones reales PostgreSQL/Supabase pendientes.
  - Impacto: no hay evidencia contra servicio real.
  - Cuando se retoma: hardening/deploy o al recibir credenciales.
- Riesgo: Redis real pendiente.
  - Impacto: rate/idempotency runtime distribuido no smokeado contra Redis real.
  - Cuando se retoma: hardening/deploy.
- Riesgo: storage privado real pendiente desde slice 02.
  - Impacto: documentos siguen sin storage real en runtime normal.
  - Cuando se retoma: hardening/deploy.
- Riesgo: smoke Telegram real no ejecutado.
  - Impacto: no valida shell real de Telegram.
  - Cuando se retoma: QA manual.
- Riesgo: TestClient warning Starlette/httpx.
  - Impacto: warning de dependencia aceptado temporalmente.
  - Cuando se retoma: hardening de toolchain.

## Auto-verificacion de Builder

- No toque scope prohibido.
- No cambie reglas de negocio fuera de slice 04.
- No cambie estados/enums sin contrato.
- No cambie disclaimers fuera del requerido.
- No expuse secretos.
- No use rutas/endpoints no aprobados.
- No cree tablas fuera del contrato.
- No deje tests fallando.
- No declare `READY_FOR_REAL_USE`.

## Estado final

```txt
READY_FOR_OWNER_REVIEW
```
