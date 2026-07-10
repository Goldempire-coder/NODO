# BUILDER_REPORT - slice_07_chat_disputes

## Slice

- Slice: `slice_07_chat_disputes`
- Estado final: `READY_FOR_OWNER_REVIEW`
- Fecha: 2026-07-04
- Builder/agente: Codex

## Scope construido

- Incluido:
  - Chat de orden entre remitter y business owner.
  - Attachments privados de mensajes.
  - Apertura de disputa por participante de la orden.
  - Admin/support/super_admin read-only para list/detail de disputas.
  - Migraciones reversibles para `messages`, `message_attachments`, `disputes`, `dispute_events`.
  - UI minima gobernada para `R-09_ORDER_TRACKING_CHAT` y `B-13_BUSINESS_CHAT`.
  - Tests, runner y evidencia de slice 07.
- Excluido:
  - Resolucion admin de disputas.
  - Confirmacion de recibido del remitente.
  - Completion, rating, auto-complete.
  - Jobs masivos.
  - Movimientos de creditos por resolucion.
  - Admin UI A-06/A-07.
  - Slice 08.
- Que NO toque:
  - No cambie reglas de creditos de slices 03-06.
  - No construi `R-10_CONFIRM_RECEIVED`.
  - No cree `chat_messages`.
  - No cree endpoint `POST /api/v1/admin/disputes/{id}/resolve`.
  - No declare `READY_FOR_REAL_USE`.

## Archivos y lineas

```txt
apps/api/app/main.py:
lineas: 13-15, 48-60, 79-80
motivo: registrar repositorios/routers chat y disputes en test/runtime.
contrato cumplido: endpoints slice 07 bajo /api/v1.
```

```txt
apps/api/app/shared/storage/private.py:
lineas: 41-50, 65-66
motivo: storage privado para message attachments.
contrato cumplido: attachments privados sin storage publico falso.
```

```txt
apps/api/app/modules/chat/*:
lineas: modulo completo
motivo: routes, schemas, service, repository, policy y modelos de mensajes/attachments.
contrato cumplido: messages canonico, no chat_messages, idempotencia, audit, rate limit, masking.
```

```txt
apps/api/app/modules/disputes/*:
lineas: modulo completo
motivo: routes, schemas, service, repository, policy y modelos de disputas.
contrato cumplido: apertura de disputa, admin read-only, sin resolve admin.
```

```txt
database/migrations/0008_slice_07_chat_disputes.up.sql:
lineas: 1-157
motivo: crear tablas/constraints/indexes del slice 07.
contrato cumplido: messages, message_attachments, disputes, dispute_events.
```

```txt
database/migrations/0008_slice_07_chat_disputes.down.sql:
lineas: 1-33
motivo: reversibilidad de migracion.
contrato cumplido: deploy rollback gate.
```

```txt
apps/web/src/app/page.tsx:
lineas: 7-21, 263-304, 425-431, 914-1017, 1087-1092, 1345-1353, 1592-1700, 1701-1758
motivo: UI R-09/B-13 y navegacion desde orden/detalle negocio.
contrato cumplido: Telegram UI surface, estados, copy NODO, sin R-10/completion/admin resolve.
```

```txt
apps/api/tests/test_chat_disputes.py:
lineas: 1-475
motivo: tests obligatorios slice 07.
contrato cumplido: ownership, idempotencia, attachments, dispute effects, no resolve endpoint.
```

```txt
scripts/run_slice_07_tests.py:
lineas: 1-83
motivo: runner gobernado y escaneo frontend.
contrato cumplido: evidencia JSON y gate de secretos/scope prohibido.
```

```txt
evidence/slice_runs/slice_07_chat_disputes_evidence.md:
lineas: 1-129
motivo: evidencia humana del slice.
contrato cumplido: evidence/slice_runs.
```

```txt
evidence/slice_runs/slice_07_chat_disputes_test_results.json:
lineas: 1-34
motivo: resultados machine-readable del runner.
contrato cumplido: evidencia JSON.
```

## Dependencias

No instale dependencias nuevas.

## Contratos cumplidos

- Governance:
  - Construido solo `slice_07_chat_disputes`.
  - No avance a slice 08.
  - No use `READY_FOR_REAL_USE`.
- Data:
  - Tablas canonicas: `messages`, `message_attachments`, `disputes`, `dispute_events`.
  - No se creo `chat_messages`.
  - `file_assets` usado para attachments privados.
- API:
  - `GET /api/v1/orders/{id}/messages`
  - `POST /api/v1/orders/{id}/messages`
  - `POST /api/v1/orders/{id}/message-attachments`
  - `POST /api/v1/orders/{id}/disputes`
  - `GET /api/v1/admin/disputes`
  - `GET /api/v1/admin/disputes/{id}`
  - No existe `POST /api/v1/admin/disputes/{id}/resolve`.
- Security:
  - Auth requerida.
  - Ownership backend.
  - Rate limit en rutas sensibles.
  - Idempotencia en mutaciones.
  - Attachments privados, sin `storage_path` en respuestas.
  - Admin/support read-only para disputas.
- UI/UX:
  - `R-09_ORDER_TRACKING_CHAT`.
  - `B-13_BUSINESS_CHAT`.
  - Estados loading/empty/error/offline/forbidden/success en la superficie.
  - Copy NODO: registra evidencia/estado, no recibe/retiene/transfiere/garantiza fondos.
- QA:
  - Tests slice 07 nuevos.
  - Runners 00-07 OK.
  - Pytest acumulado OK.
  - Frontend build OK.
  - Ruff/compileall OK.
  - Escaneo frontend OK.

## Comandos ejecutados

```txt
comando: corepack pnpm --filter @nodo/web build
resultado: OK
evidencia: build Next.js completado, ruta / generada.
```

```txt
comando: python scripts\run_slice_00_tests.py
resultado: 6 passed, 0 failed
evidencia: evidence/slice_runs/slice_00_foundation_test_results.json
```

```txt
comando: python scripts\run_slice_01_tests.py
resultado: 6 passed, 0 failed
evidencia: evidence/slice_runs/slice_01_auth_telegram_test_results.json
```

```txt
comando: python scripts\run_slice_02_tests.py
resultado: OK
evidencia: runner slice 02 exit code 0
```

```txt
comando: python scripts\run_slice_03_tests.py
resultado: OK
evidencia: runner slice 03 exit code 0
```

```txt
comando: python scripts\run_slice_04_tests.py
resultado: OK
evidencia: runner slice 04 exit code 0
```

```txt
comando: python scripts\run_slice_05_tests.py
resultado: OK
evidencia: runner slice 05 exit code 0
```

```txt
comando: python scripts\run_slice_06_tests.py
resultado: OK
evidencia: runner slice 06 exit code 0
```

```txt
comando: python scripts\run_slice_07_tests.py
resultado: OK, 7 passed, 1 warning
evidencia: evidence/slice_runs/slice_07_chat_disputes_test_results.json
```

```txt
comando: $env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
resultado: 64 passed, 1 warning
evidencia: salida pytest acumulada
```

```txt
comando: python -m ruff check apps\api scripts
resultado: All checks passed
evidencia: salida ruff
```

```txt
comando: python -m compileall apps scripts
resultado: OK
evidencia: salida compileall
```

```txt
comando: frontend source/build private-data scan
resultado: frontend scan OK
evidencia: sin hits para secretos, storage_path, account_value, rutas/copy prohibidas
```

## Tests

- Tests ejecutados:
  - Frontend build.
  - Runners 00, 01, 02, 03, 04, 05, 06, 07.
  - Pytest acumulado.
  - Ruff.
  - Compileall.
  - Escaneo frontend source/build.
- Tests no ejecutados:
  - Migraciones reales contra PostgreSQL/Supabase.
  - Redis real.
  - Storage privado real.
  - Smoke manual Telegram real.
- Razon de tests no ejecutados:
  - Riesgos heredados aceptados temporalmente por owner hasta credenciales/servicios reales y hardening/deploy.

## Evidencia

- Archivos de evidencia:
  - `evidence/slice_runs/slice_07_chat_disputes_evidence.md`
- Resultados JSON/logs:
  - `evidence/slice_runs/slice_07_chat_disputes_test_results.json`
- Capturas si aplica:
  - No aplica; se ejecuto build frontend y tests automatizados.

## Riesgos residuales

- Riesgo: migraciones reales contra PostgreSQL/Supabase pendientes.
  - Impacto: no valida DDL contra servicio real.
  - Cuando se retoma: hardening/deploy.
- Riesgo: Redis real pendiente.
  - Impacto: rate/idempotency runtime no probado contra servicio real.
  - Cuando se retoma: hardening/deploy.
- Riesgo: storage privado real pendiente.
  - Impacto: attachments usan adapter in-memory en test; runtime normal responde error seguro si no hay storage.
  - Cuando se retoma: hardening/deploy/storage.
- Riesgo: smoke manual Telegram real pendiente.
  - Impacto: experiencia real Mini App no validada en cliente Telegram.
  - Cuando se retoma: QA manual.
- Riesgo: Starlette/httpx warning heredado.
  - Impacto: no bloquea tests actuales.
  - Cuando se retoma: mantenimiento de dependencias.

## Auto-verificacion de Builder

- No toque scope prohibido: confirmado.
- No cambie reglas de negocio: confirmado.
- No cambie estados/enums sin contrato: confirmado.
- No cambie disclaimers: confirmado, mantuve responsabilidad NODO.
- No expuse secretos: confirmado por scan.
- No use rutas/endpoints no aprobados: confirmado.
- No cree tablas fuera del contrato: confirmado.
- No deje tests fallando: confirmado.
- No declare `READY_FOR_REAL_USE`: confirmado.

## Estado final permitido

```txt
READY_FOR_OWNER_REVIEW
```
