# BUILDER_REPORT - slice_03_ads_marketplace

## Slice

- Slice: `slice_03_ads_marketplace`
- Estado final: `READY_FOR_OWNER_REVIEW`
- Fecha: 2026-07-04
- Builder/agente: Codex

## Scope construido

- Incluido:
  - Backend modular `ads` con routes, schemas, service, repository, policy/RBAC, state machine y ranking/search service.
  - Credit hold/release service dentro del modulo `ads`, con wallet lazy y ledger append-only.
  - Migracion reversible para `ads`, `credit_wallets` y `credits_ledger`.
  - Endpoints autorizados:
    - `GET /api/v1/ads/search`
    - `GET /api/v1/ads/{id}`
    - `POST /api/v1/business/ads`
    - `GET /api/v1/business/ads`
    - `GET /api/v1/business/ads/archived`
    - `PUT /api/v1/business/ads/{id}`
    - `POST /api/v1/business/ads/{id}/pause`
    - `POST /api/v1/business/ads/{id}/archive`
  - UI minima gobernada para R-02, R-03, R-04, B-08, B-09 y B-10 dentro del entry autenticado existente.
  - Tests backend slice 03, runner slice 03, evidencia JSON/MD.
- Excluido:
  - Ordenes, pagos reales, chat, disputas, Stripe, referrals, jobs masivos, admin completo y slices posteriores.
- Que NO toque:
  - No avance a slice 04.
  - No cambie reglas de creditos fuera del contrato.
  - No cambie disclaimers.
  - No cree rutas legacy ni endpoints fuera del contrato.
  - No expuse datos privados del negocio.

## Archivos y lineas

```txt
apps/api/app/modules/ads/models.py:
lineas: 1-88
motivo: modelos in-memory de ads, credit wallets y ledger.
contrato cumplido: DATA_CONTRACT, ENUMS_AND_STATUS_MASTER.
```

```txt
apps/api/app/modules/ads/schemas.py:
lineas: 1-29
motivo: payloads validados para create/update/search de anuncios.
contrato cumplido: ADS_API.
```

```txt
apps/api/app/modules/ads/policy.py:
lineas: 1-26
motivo: RBAC para remitter marketplace, owner mutacion y negocio publicable.
contrato cumplido: RBAC_PERMISSION_MATRIX, SECURITY_CONTRACT.
```

```txt
apps/api/app/modules/ads/state_machine.py:
lineas: 1-32
motivo: reglas de expiracion, update, pause y archive.
contrato cumplido: AD_LIFECYCLE_MASTER, STATE_CONTRACT.
```

```txt
apps/api/app/modules/ads/repository.py:
lineas: 55-248, 250-598
motivo: repositorio in-memory/PostgreSQL para ads, wallet lazy, hold/release ledger, listados y search.
contrato cumplido: DATA_CONTRACT, DATABASE_CONSTRAINTS, INDEXES.
```

```txt
apps/api/app/modules/ads/service.py:
lineas: 18-33, 67-314
motivo: calculo de creditos, publicacion, idempotencia, audit, expiracion pasiva, search/detail y mutaciones.
contrato cumplido: ADS_API, CREDITS_AND_BILLING_MASTER, AUDIT_EVENTS, ERROR_CONTRACT.
```

```txt
apps/api/app/modules/ads/routes.py:
lineas: 1-121
motivo: endpoints canonicos autorizados del slice 03.
contrato cumplido: API_CONTRACT.
```

```txt
apps/api/app/modules/businesses/repository.py:
lineas: 202-208, 388-430
motivo: helpers seguros para validar payment methods y ids de negocios elegibles para marketplace.
contrato cumplido: ADS_API, SECURITY_CONTRACT.
```

```txt
apps/api/app/main.py:
lineas: 7-9, 40, 48, 66
motivo: wiring del repositorio/router `ads`.
contrato cumplido: CODE_ARCHITECTURE_MASTER.
```

```txt
apps/api/app/core/errors.py:
lineas: 28-37
motivo: errores seguros del slice 03.
contrato cumplido: ERROR_CONTRACT.
```

```txt
database/migrations/0004_slice_03_ads_marketplace.up.sql:
lineas: 1-137
motivo: tablas, constraints, FKs e indices de ads/credit wallets/ledger.
contrato cumplido: DATA_CONTRACT, DATABASE_CONSTRAINTS, INDEXES.
```

```txt
database/migrations/0004_slice_03_ads_marketplace.down.sql:
lineas: 1-17
motivo: rollback reversible.
contrato cumplido: migration reversibility.
```

```txt
apps/web/src/app/page.tsx:
lineas: 13-17, 342-444, 632-664, 776-908
motivo: UI minima de marketplace, detalle, crear anuncio, mis anuncios y archivados.
contrato cumplido: UI_CONTRACT, R-02, R-03, R-04, B-08, B-09, B-10.
```

```txt
apps/web/src/app/globals.css:
lineas: 32-37, 98-140
motivo: estilos para selects, grid de montos y filas compactas de anuncios.
contrato cumplido: DESIGN_TOKENS, TELEGRAM_MINI_APP_RULES.
```

```txt
apps/api/tests/test_ads_marketplace.py:
lineas: 1-400
motivo: tests obligatorios del slice 03.
contrato cumplido: QA, SECURITY_TESTS.
```

```txt
scripts/run_slice_03_tests.py:
lineas: 1-60
motivo: runner slice 03 y JSON evidence.
contrato cumplido: QA evidence.
```

```txt
evidence/slice_runs/slice_03_ads_marketplace_test_results.json:
lineas: 1-24
motivo: resultados machine-readable del runner.
contrato cumplido: evidence.
```

```txt
evidence/slice_runs/slice_03_ads_marketplace_evidence.md:
lineas: 1-96
motivo: evidencia humana de comandos, contratos y riesgos.
contrato cumplido: evidence.
```

## Dependencias

```txt
paquete: ninguno nuevo registrado
version: n/a
archivo donde quedo registrado: n/a
motivo: se uso stack existente de slices 00-02.
contrato que la permite: stack aprobado del proyecto.
```

## Contratos cumplidos

- Governance: se construyo solo `slice_03_ads_marketplace`; no se avanzo a slice 04; no se cambio estado de uso real del producto.
- Data: `ads`, `credit_wallets`, `credits_ledger`, constraints, FKs e indices contractuales.
- API: endpoints canonicos implementados; no se creo ruta legacy `/ads` mutante ni `PATCH /ads/{id}/pause`.
- Security: auth requerida, RBAC owner/remitter, negocios aprobados, rate limits, idempotencia, errores seguros, no datos privados en frontend/logs.
- Credits: hold al publicar, release al expirar/archivar cuando aplica, founder access vigente sin debit, ledger append-only.
- Ads: estados oficiales, publicacion directa MVP, expiracion pasiva, search excluye vencidos, detail/click no consume creditos.
- UI/UX: pantallas gobernadas agregadas en la Mini App existente, sin landing comercial, con estados loading/empty/error/offline/success via notice y listas.
- QA: tests slice 00/01/02/03, pytest acumulado, build frontend, ruff, compileall y scan de secretos ejecutados.

## Comandos ejecutados

```txt
comando: $env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_ads_marketplace.py -q
resultado: 11 passed, 1 Starlette/httpx warning.
evidencia: terminal output; evidence/slice_runs/slice_03_ads_marketplace_test_results.json
```

```txt
comando: python scripts\run_slice_03_tests.py
resultado: OK; pytest slice 03 11 passed, compileall OK, frontend secret/private-data scan OK.
evidencia: evidence/slice_runs/slice_03_ads_marketplace_test_results.json
```

```txt
comando: corepack pnpm --filter @nodo/web build
resultado: OK; Next.js compiled and type-checked.
evidencia: terminal output.
```

```txt
comando: python scripts\run_slice_00_tests.py
resultado: passed 6, failed 0.
evidencia: evidence/slice_runs/slice_00_foundation_test_results.json
```

```txt
comando: python scripts\run_slice_01_tests.py
resultado: passed 6, failed 0.
evidencia: evidence/slice_runs/slice_01_auth_telegram_test_results.json
```

```txt
comando: python scripts\run_slice_02_tests.py
resultado: OK; pytest slice 02 9 passed, compileall OK, scan OK.
evidencia: evidence/slice_runs/slice_02_business_verification_test_results.json
```

```txt
comando: $env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
resultado: 35 passed, 1 Starlette/httpx warning.
evidencia: terminal output.
```

```txt
comando: python -m ruff check apps\api scripts
resultado: All checks passed.
evidencia: terminal output.
```

```txt
comando: python -m compileall apps/api scripts
resultado: OK.
evidencia: terminal output.
```

```txt
comando: rg -n "BOT_TOKEN|JWT_SECRET|JWT_REFRESH_SECRET|owner@example\.com|storage_path|account_value|BEGIN PRIVATE KEY|AKIA[0-9A-Z]{16}" apps\web\src apps\web\.next
resultado: exit 1, no matches.
evidencia: terminal output.
```

## Tests

- Tests ejecutados:
  - Crear anuncio solo con negocio aprobado.
  - No crear anuncio con negocio no aprobado.
  - No crear anuncio de negocio ajeno.
  - No crear sin creditos/founder access valido.
  - Costos 1/2/3 por rango.
  - `> 2000` bloqueado.
  - Payment method pertenece al negocio, esta approved y active.
  - Rango solapado activo bloqueado.
  - Search solo devuelve active/no vencidos/approved.
  - Detail/click no consume creditos.
  - Pause no cambia `expires_at` ni libera creditos.
  - Archive solo desde paused/expired.
  - Expiracion pasiva materializa expired y audita.
  - Expiracion sin orden libera hold.
  - Idempotency create/update/pause/archive.
  - Rate limit search/list y mutaciones sensibles.
  - Audit events de ads y creditos.
  - No secrets ni datos privados en frontend/logs.
  - Frontend build.
  - Backend tests acumulados.
  - Slice 00, 01, 02 y 03 runners.
  - Ruff.
  - Compileall.
  - Escaneo frontend source/build.
- Tests no ejecutados:
  - Migraciones reales contra PostgreSQL/Supabase.
  - Redis real.
  - Smoke manual dentro de Telegram real.
- Razon de tests no ejecutados:
  - No hay credenciales/servicios reales configurados para Postgres/Supabase o Redis.
  - Telegram real requiere entorno externo de Mini App.

## Evidencia

- Archivos de evidencia:
  - `evidence/slice_runs/slice_03_ads_marketplace_evidence.md`
  - `evidence/slice_runs/slice_03_ads_marketplace_test_results.json`
- Resultados JSON/logs:
  - `slice_03_ads_marketplace_test_results.json`: pytest slice 03 11 passed, compileall OK, frontend scan OK.
- Capturas si aplica:
  - No aplica; contrato exigio build frontend y escaneo, no screenshot obligatoria.

## Riesgos residuales

- Riesgo: migraciones reales contra PostgreSQL/Supabase pendientes.
  - Impacto: DDL no fue aplicado contra servicio real.
  - Cuando se retoma: hardening/deploy o cuando existan credenciales/servicios.
- Riesgo: Redis real pendiente.
  - Impacto: rate limit/idempotency runtime real no probado contra servicio real en esta corrida.
  - Cuando se retoma: hardening/deploy o cuando exista Redis real.
- Riesgo: storage privado real pendiente heredado.
  - Impacto: slice 03 no agrega storage nuevo; el riesgo sigue para documentos slice 02.
  - Cuando se retoma: hardening/deploy de storage.
- Riesgo: warning Starlette/httpx TestClient.
  - Impacto: no bloquea tests; heredado y aceptado temporalmente.
  - Cuando se retoma: hardening/dependency alignment.
- Riesgo: no hay credit purchase/admin credit funding en este slice.
  - Impacto: businesses sin founder access o credit seed no pueden publicar, como exige el contrato.
  - Cuando se retoma: slice de creditos/referrals aprobado.

## Auto-verificacion de Builder

- No toque scope prohibido.
- No cambie reglas de negocio.
- No cambie estados/enums sin contrato.
- No cambie disclaimers.
- No expuse secretos.
- No use rutas/endpoints no aprobados.
- No cree tablas fuera del contrato.
- No deje tests fallando.
- No avance a slice 04.
- No declare estado de uso real del producto.

## Estado final permitido

```txt
READY_FOR_OWNER_REVIEW
```
