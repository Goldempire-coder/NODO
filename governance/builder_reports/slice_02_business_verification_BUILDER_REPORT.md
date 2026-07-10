# BUILDER_REPORT - slice_02_business_verification

## Slice

- Slice: `slice_02_business_verification`
- Estado final: `READY_FOR_OWNER_REVIEW`
- Fecha: 2026-07-04
- Builder/agente: Codex

## Scope construido

- Incluido:
  - Backend modular `businesses` con routes, schemas, service, repository, policy y state machine.
  - Migracion reversible para `businesses`, `business_verification_submissions`, `business_payment_methods` y `file_assets`.
  - Endpoints autorizados de business owner y admin verification.
  - Upload privado de documentos de verificacion con validacion de file_type, MIME y max 5 MB.
  - Idempotencia para create/update/submit/approve/reject.
  - Rate limit para endpoints sensibles.
  - Audit events obligatorios.
  - UI minima gobernada para B-01, B-02, B-03, A-02 y A-03 dentro del entry autenticado.
  - Tests backend slice 02, runner slice 02, evidencia JSON/MD.
- Excluido:
  - Marketplace, anuncios, ordenes, pagos reales, creditos reales, disputas, chat, referrals, jobs fuera del slice, admin completo.
- Que NO toque:
  - No cambie disclaimers.
  - No cambie estados/enums fuera del contrato corregido.
  - No cree pantallas finales fuera de auth/business verification.
  - No declare `READY_FOR_REAL_USE`.

## Archivos y lineas

```txt
apps/api/app/main.py:
lineas: 3, 7-18, 36-47, 60, 68-71
motivo: registrar repositorio business, idempotencia, storage privado, router slice 02 y handler seguro de validation errors.
contrato cumplido: API, Security, Architecture.
```

```txt
apps/api/app/core/config.py:
lineas: 47-49, 95-97
motivo: configurar rate limit business y TTL maximo de signed URL.
contrato cumplido: RATE_LIMIT_POLICY, SECURITY_CONTRACT.
```

```txt
apps/api/app/core/errors.py:
lineas: 13-28
motivo: agregar errores seguros esperados por businesses/admin/idempotency/storage.
contrato cumplido: ERROR_CONTRACT.
```

```txt
apps/api/app/modules/users/repository.py:
lineas: 95-99, 205-208
motivo: permitir promocion gobernada a `business_owner` al crear negocio propio.
contrato cumplido: USER_ROLES, BUSINESSES_API.
```

```txt
apps/api/app/shared/idempotency/store.py:
lineas: 1-89
motivo: idempotencia in-memory test y Redis runtime para endpoints mutantes.
contrato cumplido: API idempotency, RATE_LIMIT_POLICY.
```

```txt
apps/api/app/shared/storage/private.py:
lineas: 1-41
motivo: storage privado test y runtime seguro sin URL falsa cuando no hay storage real.
contrato cumplido: SENSITIVE_DATA_POLICY, SECURITY_CONTRACT.
```

```txt
apps/api/app/modules/businesses/models.py:
lineas: 1-92
motivo: modelos y constantes oficiales de estados, documentos, MIME y limites.
contrato cumplido: DATA_CONTRACT, ENUMS_AND_STATUS_MASTER.
```

```txt
apps/api/app/modules/businesses/schemas.py:
lineas: 1-43
motivo: payloads validados para business owner/admin.
contrato cumplido: BUSINESSES_API, ADMIN_API.
```

```txt
apps/api/app/modules/businesses/policy.py:
lineas: 1-30
motivo: RBAC owner/admin/support separado del servicio.
contrato cumplido: RBAC_PERMISSION_MATRIX.
```

```txt
apps/api/app/modules/businesses/state_machine.py:
lineas: 1-34
motivo: validacion de estados permitidos para owner submit/update/upload y admin review.
contrato cumplido: STATE_CONTRACT.
```

```txt
apps/api/app/modules/businesses/repository.py:
lineas: 1-410
motivo: persistencia in-memory y PostgreSQL para business, submissions, payment methods y file assets.
contrato cumplido: DATA_CONTRACT, DATABASE_CONSTRAINTS, INDEXES.
```

```txt
apps/api/app/modules/businesses/service.py:
lineas: 84-364
motivo: reglas de negocio del slice, audit, masking, idempotencia, signed URL y review.
contrato cumplido: BUSINESSES_API, ADMIN_API, SECURITY_CONTRACT, AUDIT_EVENTS.
```

```txt
apps/api/app/modules/businesses/routes.py:
lineas: 1-211
motivo: endpoints autorizados, auth dependency, multipart parsing y response contract.
contrato cumplido: API_CONTRACT.
```

```txt
database/migrations/0003_slice_02_business_verification.up.sql:
lineas: 1-145
motivo: tablas, constraints e indices del slice.
contrato cumplido: DATA_CONTRACT, DATABASE_CONSTRAINTS, INDEXES.
```

```txt
database/migrations/0003_slice_02_business_verification.down.sql:
lineas: 1-4
motivo: rollback reversible.
contrato cumplido: migration reversibility.
```

```txt
apps/web/src/app/page.tsx:
lineas: 47-50, 135-396
motivo: UI minima auth/business/admin con Telegram SDK/UI, MainButton y estados del slice.
contrato cumplido: TELEGRAM_MINI_APP_RULES, UI_CONTRACT, screen contracts B-01/B-02/B-03/A-02/A-03.
```

```txt
apps/web/src/app/globals.css:
lineas: 38-91
motivo: estilos para shell business/admin con tokens existentes y reduced motion preservado.
contrato cumplido: DESIGN_TOKENS, MOTION_AND_INTERACTION.
```

```txt
apps/api/tests/test_business_verification.py:
lineas: 149-395
motivo: tests obligatorios de owner, admin, support, uploads, idempotencia, rate limit y fugas.
contrato cumplido: QA, SECURITY_TESTS.
```

```txt
scripts/run_slice_02_tests.py:
lineas: 1-47
motivo: runner slice 02 y JSON evidence.
contrato cumplido: QA evidence.
```

```txt
evidence/slice_runs/slice_02_business_verification_test_results.json:
lineas: 1-22
motivo: resultados machine-readable del runner.
contrato cumplido: evidence.
```

```txt
evidence/slice_runs/slice_02_business_verification_evidence.md:
lineas: 1-75
motivo: evidencia humana de comandos, contratos y riesgos.
contrato cumplido: evidence.
```

## Dependencias

```txt
paquete: ninguno nuevo registrado
version: n/a
archivo donde quedo registrado: n/a
motivo: se uso stack existente; `python -m pip install --user -r apps\api\requirements.txt` reporto requirements already satisfied.
contrato que la permite: stack aprobado foundation/auth.
```

Nota: no se agrego `python-multipart`; el endpoint multipart se parsea con libreria estandar para evitar dependencia nueva.

## Contratos cumplidos

- Governance: slice 02 solamente; no se avanzo a slice 03; no se uso `READY_FOR_REAL_USE`.
- Data: tablas contractuales, constraints de estados oficiales, indexes y rollback.
- API: endpoints autorizados implementados; no se creo `/auth/telegram-login`; responses usan envelope existente.
- Security: RBAC owner/admin/support, reason obligatorio, signed URL corta, no `storage_path` expuesto, no secrets en frontend build/source.
- UI/UX: entry/auth preservado; UI minima de B-01/B-02/B-03/A-02/A-03; Telegram UI SDK y MainButton usados donde aplica; no landing comercial.
- QA: tests slice 00/01/02, pytest acumulado, build frontend, ruff, compileall y scan de secretos ejecutados.

## Comandos ejecutados

```txt
comando: python -m pip install --user -r apps\api\requirements.txt
resultado: OK; requirements already satisfied; no dependencia nueva registrada.
evidencia: terminal output.
```

```txt
comando: corepack pnpm --filter @nodo/web build
resultado: OK; Next.js compiled successfully.
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
resultado: OK; pytest slice 02 9 passed, compileall OK, secret/source scan OK.
evidencia: evidence/slice_runs/slice_02_business_verification_test_results.json
```

```txt
comando: python -m pytest apps\api\tests -q
resultado: 24 passed, 1 Starlette/httpx warning.
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
comando: rg -n "BOT_TOKEN|JWT_SECRET|JWT_REFRESH_SECRET|test-bot-token|test-access-secret|test-refresh-secret|storage_path|refresh_token" apps\web\src apps\web\.next
resultado: exit 1, no matches.
evidencia: terminal output.
```

## Tests

- Tests ejecutados:
  - Crear negocio propio.
  - Guest no crea negocio.
  - No multiples negocios activos.
  - Owner no edita negocio ajeno ni campos admin.
  - Submit exige documentos requeridos.
  - No duplica submission pendiente.
  - Upload rechaza MIME invalido y archivo mayor a 5 MB.
  - Upload no expone `storage_path`.
  - Admin lista pending con paginacion.
  - Support no aprueba/rechaza.
  - Admin approve exige reason via schema y approve/reject exige latest pending.
  - Approve genera audit; reject path protegido despues de approve.
  - Signed URL exige admin/super_admin, reason y audit.
  - Signed URL no se persiste en audit.
  - Rate limits en endpoints sensibles.
  - Errores/responses sin tokens, secretos ni storage paths.
  - Frontend build.
  - Backend tests acumulados.
  - Ruff.
  - Compileall.
  - Slice 00, slice 01 y slice 02 runners.
  - Escaneo de secretos frontend source/build.
- Tests no ejecutados:
  - Migraciones contra PostgreSQL/Supabase real.
  - Readiness success contra Redis real.
  - Storage privado real con proveedor externo.
  - Smoke manual dentro de Telegram real.
- Razon de tests no ejecutados:
  - No hay credenciales/servicios reales configurados para Postgres/Supabase, Redis o storage.
  - Telegram real requiere entorno de Mini App externo a esta corrida.

## Evidencia

- Archivos de evidencia:
  - `evidence/slice_runs/slice_02_business_verification_evidence.md`
  - `evidence/slice_runs/slice_02_business_verification_test_results.json`
- Resultados JSON/logs:
  - `slice_02_business_verification_test_results.json`: pytest slice 02 9 passed, compileall OK, secret/source scan OK.
- Capturas si aplica:
  - No aplica en esta corrida; el contrato exigio frontend build, no screenshot obligatoria.

## Riesgos residuales

- Riesgo: migraciones reales contra PostgreSQL/Supabase pendientes.
  - Impacto: no hay confirmacion contra servicio real.
  - Cuando se retoma: hardening/deploy o cuando existan credenciales/servicios.
- Riesgo: readiness success contra Redis real pendiente.
  - Impacto: Redis runtime no probado contra servicio real.
  - Cuando se retoma: hardening/deploy o cuando exista Redis real.
- Riesgo: storage real no configurado.
  - Impacto: uploads/view-url runtime normal devuelven `STORAGE_UNAVAILABLE`; test usa adapter privado controlado.
  - Cuando se retoma: slice/hardening de storage real aprobado.
- Riesgo: warning Starlette/httpx TestClient.
  - Impacto: no bloquea tests; heredado y aceptado temporalmente.
  - Cuando se retoma: hardening/dependency alignment.

## Auto-verificacion de Builder

- No toque scope prohibido.
- No cambie reglas de negocio.
- No cambie estados/enums sin contrato.
- No cambie disclaimers.
- No expuse secretos.
- No use rutas/endpoints no aprobados.
- No cree tablas fuera del contrato.
- No deje tests fallando.
- No declare `READY_FOR_REAL_USE`.

## Estado final permitido

```txt
READY_FOR_OWNER_REVIEW
```
