# BUILDER REPORT - slice_05_payment_instructions_reports

## Slice

- Slice: `slice_05_payment_instructions_reports`
- Estado final: `READY_FOR_OWNER_REVIEW`
- Fecha: 2026-07-04
- Builder/agente: Codex

No se declara `READY_FOR_REAL_USE`.

## Scope construido

- Incluido:
  - Reveal controlado de instrucciones completas de pago.
  - Upload privado de evidencia de pago usando `file_assets`.
  - Reporte de pago del remitter.
  - Transicion `waiting_payment -> payment_reported`.
  - `payment_reports.status = submitted`.
  - Audit events `payment_instructions_viewed`, `payment_evidence_uploaded`, `payment_reported`.
  - `order_state_events` para reporte de pago.
  - UI gobernada para `R-07_PAYMENT_INSTRUCTIONS` y `R-08_REPORT_PAYMENT`.
  - Migracion reversible `0006_slice_05_payment_instructions_reports`.
  - Tests y runner de slice 05.
  - Evidencia en `evidence/slice_runs/`.
- Excluido:
  - Confirmacion/rechazo del negocio.
  - Entrega/pago movil.
  - Chat.
  - Disputas.
  - Jobs masivos.
  - Consumo de creditos.
  - Compra/acreditacion real de creditos.
  - Slice 06.
- Que NO toque:
  - Reglas de negocio fuera de slice 05.
  - Estados/enums sin contrato.
  - Disclaimers fuera del copy requerido.
  - Rutas legacy fuera de `/api/v1`.
  - Tablas `payment_evidence_files` o `storage_objects`.

## Archivos y lineas

```txt
apps/api/app/modules/orders/models.py
lineas: 88
motivo: modelo interno `PaymentReportRecord`.
contrato cumplido: DATA_CONTRACT payment_reports.
```

```txt
apps/api/app/modules/orders/schemas.py
lineas: 25-43
motivo: payload validado de `PaymentReportRequest`.
contrato cumplido: PAYMENT_REPORTS_API, metodo Zelle/USDT TRC20.
```

```txt
apps/api/app/shared/storage/private.py
lineas: 31-38, 52-53
motivo: adapter controlado para evidencia privada en test y error seguro en runtime normal sin storage.
contrato cumplido: SECURITY_CONTRACT storage privado, STORAGE_UNAVAILABLE.
```

```txt
apps/api/app/modules/orders/repository.py
lineas: 70-98, 112-113, 187-269, 416-523
motivo: repositorio in-memory/Postgres para payment_reports y payment evidence en file_assets.
contrato cumplido: arquitectura modular, DATA_CONTRACT, idempotencia, storage_path no publico.
```

```txt
apps/api/app/modules/orders/state_machine.py
lineas: 42-57
motivo: guards para reveal y payment report.
contrato cumplido: STATE_CONTRACT waiting_payment y vencimiento.
```

```txt
apps/api/app/modules/orders/service.py
lineas: 25-45, 315-568
motivo: reglas de reveal, evidence upload, report payment, audit, masking, idempotencia y no consumo de creditos.
contrato cumplido: API, seguridad, lifecycle, audit, sensitive data.
```

```txt
apps/api/app/modules/orders/routes.py
lineas: 88-134
motivo: endpoints canonicos autorizados del slice 05.
contrato cumplido: PAYMENT_REPORTS_API y slice API_CONTRACT.
```

```txt
apps/api/app/core/errors.py
lineas: 49-54
motivo: errores seguros para report/evidence/storage.
contrato cumplido: ERROR_CONTRACT.
```

```txt
apps/api/requirements.txt
lineas: 11
motivo: registrar dependencia multipart requerida por FastAPI para uploads.
contrato cumplido: dependencias permitidas del stack backend.
```

```txt
database/migrations/0006_slice_05_payment_instructions_reports.up.sql
lineas: 1-66
motivo: crear payment_reports, ampliar file_assets para payment_evidence, constraints e indices.
contrato cumplido: DATA_MODEL_MASTER, DATABASE_CONSTRAINTS, INDEXES, DATA_CONTRACT.
```

```txt
database/migrations/0006_slice_05_payment_instructions_reports.down.sql
lineas: 1-19
motivo: rollback reversible del slice 05.
contrato cumplido: migration reversibility.
```

```txt
apps/web/src/app/page.tsx
lineas: 17-18, 207-209, 568-658, 819-829, 1211-1303
motivo: UI R-07/R-08, reveal owner-only desde API, upload evidence, report payment y copy obligatorio.
contrato cumplido: UI_CONTRACT, TELEGRAM Mini App rules, sensitive data masking.
```

```txt
apps/web/src/app/globals.css
lineas: 128-138
motivo: estilo para bloque de instrucciones de pago.
contrato cumplido: UI gobernada sin landing generica.
```

```txt
apps/api/tests/test_payment_instructions_reports.py
lineas: 1-375
motivo: tests obligatorios del slice 05.
contrato cumplido: QA.md, SECURITY_TESTS y contratos de API/state/data.
```

```txt
scripts/run_slice_05_tests.py
lineas: 11-69
motivo: runner y evidencia JSON de slice 05.
contrato cumplido: evidencia obligatoria.
```

```txt
evidence/slice_runs/slice_05_payment_instructions_reports_evidence.md
lineas: 1-177
motivo: evidencia humana del slice.
contrato cumplido: evidencia obligatoria.
```

```txt
evidence/slice_runs/slice_05_payment_instructions_reports_test_results.json
lineas: 1-31
motivo: resultados JSON generados por runner.
contrato cumplido: evidencia obligatoria.
```

## Dependencias

```txt
paquete: python-multipart
version: 0.0.32 instalada; constraint python-multipart>=0.0.20,<1.0.0
archivo donde quedo registrado: apps/api/requirements.txt
motivo: FastAPI requiere parser multipart para `POST /api/v1/orders/{id}/payment-evidence`
contrato que la permite: dependencias backend permitidas para FastAPI/test foundation
```

## Endpoints construidos

- `GET /api/v1/orders/{id}/payment-instructions`
- `POST /api/v1/orders/{id}/payment-evidence`
- `POST /api/v1/orders/{id}/payment-report`

## Migraciones creadas

- `database/migrations/0006_slice_05_payment_instructions_reports.up.sql`
- `database/migrations/0006_slice_05_payment_instructions_reports.down.sql`

## Contratos cumplidos

- Governance:
  - Solo se construyo `slice_05_payment_instructions_reports`.
  - No se avanzo a `slice_06`.
  - No se declaro `READY_FOR_REAL_USE`.
- Data:
  - `payment_reports` creado con estado inicial `submitted`.
  - `file_assets` usado como entidad canonica para evidencia privada.
  - No se crearon `payment_evidence_files` ni `storage_objects`.
  - Constraints e indices del slice 05 agregados.
- API:
  - Rutas canonicas bajo `/api/v1`.
  - `payment-instructions` no crea report ni cambia estado.
  - `payment-report` cambia solo `waiting_payment -> payment_reported`.
  - Idempotencia implementada en payment report y evidence.
- Security:
  - Auth obligatoria.
  - Ownership estricto por remitter.
  - No se exponen instrucciones completas fuera de R-07/endpoint reveal.
  - No se expone `storage_path`.
  - Logs/audit no guardan datos sensibles completos.
  - Runtime normal sin storage privado responde error seguro.
- UI/UX:
  - R-07 y R-08 implementadas dentro de la app existente.
  - Copy obligatorio de responsabilidad entre partes incluido.
  - No landing comercial.
  - No chat ni R-09.
- QA:
  - Tests focales slice 05.
  - Pytest acumulado backend.
  - Runners 00-05.
  - Frontend build.
  - Ruff.
  - Compileall.
  - Secret/private-data scan frontend.

## Comandos ejecutados

```txt
comando: python -m pip install "python-multipart>=0.0.20,<1.0.0"
resultado: OK, python-multipart 0.0.32 instalado
evidencia: apps/api/requirements.txt
```

```txt
comando: $env:PYTHONPATH='apps/api'; python -m pytest apps/api/tests/test_payment_instructions_reports.py -q
resultado: 7 passed, 1 warning
evidencia: evidence/slice_runs/slice_05_payment_instructions_reports_test_results.json
```

```txt
comando: $env:PYTHONPATH='apps/api'; python -m pytest apps/api/tests -q
resultado: 51 passed, 1 warning
evidencia: salida de consola
```

```txt
comando: python -m ruff check apps/api scripts
resultado: All checks passed!
evidencia: salida de consola
```

```txt
comando: python -m compileall apps/api scripts
resultado: OK
evidencia: salida de consola y runner slice 05
```

```txt
comando: corepack pnpm --filter @nodo/web build
resultado: OK
evidencia: salida de consola
```

```txt
comando: python scripts\run_slice_00_tests.py
resultado: OK, 6 passed
evidencia: salida de consola
```

```txt
comando: python scripts\run_slice_01_tests.py
resultado: OK, 6 passed
evidencia: salida de consola
```

```txt
comando: python scripts\run_slice_02_tests.py
resultado: OK
evidencia: evidence/slice_runs/slice_02_business_verification_test_results.json
```

```txt
comando: python scripts\run_slice_03_tests.py
resultado: OK
evidencia: evidence/slice_runs/slice_03_ads_marketplace_test_results.json
```

```txt
comando: python scripts\run_slice_04_tests.py
resultado: OK
evidencia: evidence/slice_runs/slice_04_order_creation_test_results.json
```

```txt
comando: python scripts\run_slice_05_tests.py
resultado: OK, 7 passed, 1 warning; compileall OK; frontend scan sin hits
evidencia: evidence/slice_runs/slice_05_payment_instructions_reports_test_results.json
```

```txt
comando: rg -n "BOT_TOKEN|JWT_SECRET|JWT_REFRESH_SECRET|test-bot-token|test-access-secret|test-refresh-secret|owner@example\.com|storage_path|account_value|payment_instructions_snapshot|BEGIN PRIVATE KEY|AKIA[0-9A-Z]{16}" apps/web/src apps/web/.next
resultado: exit 1, sin matches
evidencia: salida de consola
```

## Tests

- Tests ejecutados:
  - reveal own waiting_payment order OK.
  - reveal orden ajena bloqueada sin filtrar existencia.
  - reveal vencida bloqueada.
  - reveal setea `payment_data_revealed_at/by`.
  - reveal audita `payment_instructions_viewed`.
  - reveal no crea payment report.
  - reveal no cambia status.
  - report Zelle valido cambia `waiting_payment -> payment_reported`.
  - report USDT valido cambia `waiting_payment -> payment_reported`.
  - report metodo invalido falla.
  - report sin evidencia requerida falla para Zelle.
  - report vencida falla.
  - report orden ajena falla seguro.
  - report no consume creditos.
  - report deja ad `in_order`.
  - report deja creditos bloqueados.
  - report no confirma negocio.
  - report no entrega.
  - idempotent retry devuelve mismo resultado.
  - misma idempotency key con payload distinto falla.
  - upload evidence owner-only.
  - upload evidence devuelve/acepta `pending_payment_report_id`.
  - Zelle report valida `proof_file_id` y `pending_payment_report_id`.
  - upload evidence rechaza MIME invalido.
  - upload evidence rechaza archivo mayor a 5 MB.
  - upload evidence no expone `storage_path`.
  - audit events.
  - state events.
  - frontend build.
  - runners 00, 01, 02, 03, 04, 05.
  - backend pytest acumulado.
  - ruff.
  - compileall.
  - frontend secret/private-data scan.
- Tests no ejecutados:
  - Migraciones contra PostgreSQL/Supabase real.
  - Redis real.
  - Storage privado real.
  - Smoke manual Telegram real.
- Razon de tests no ejecutados:
  - Riesgos residuales heredados y aceptados temporalmente por falta de servicios/credenciales reales.

## Evidencia

- Archivos de evidencia:
  - `evidence/slice_runs/slice_05_payment_instructions_reports_evidence.md`
  - `evidence/slice_runs/slice_05_payment_instructions_reports_test_results.json`
- Resultados JSON/logs:
  - `slice_05_payment_instructions_reports_test_results.json`: focal pytest 7 passed, compileall OK, frontend scan hits [].
- Capturas si aplica:
  - No aplica.

## Evidencia especifica solicitada

- Reveal controlado:
  - `payment_instructions` exige owner, status `waiting_payment`, no vencida, setea reveal fields y audita `payment_instructions_viewed`.
- Reportar pago no consume creditos:
  - Test valida que los contadores de wallet no cambian durante `payment-report`.
- Ad queda `in_order`:
  - Test valida que `ad.status` se mantiene `in_order` despues de reportar pago.
- `storage_path` no se expone:
  - Tests y scan frontend validan ausencia de `storage_path` en responses/source/build.
- Idempotencia:
  - Test valida replay exitoso con misma key/payload y conflicto con misma key/payload distinto.

## Riesgos residuales

```txt
riesgo: migraciones reales contra PostgreSQL/Supabase pendientes
impacto: aun no hay evidencia contra base real
cuando se retoma: hardening/deploy con credenciales reales
```

```txt
riesgo: Redis real pendiente
impacto: rate limit/readiness real sigue sin prueba de servicio externo
cuando se retoma: hardening/deploy con Redis real
```

```txt
riesgo: storage privado real pendiente
impacto: runtime normal devuelve error seguro `STORAGE_UNAVAILABLE` hasta configurar adapter real
cuando se retoma: hardening/deploy o slice de storage real
```

```txt
riesgo: smoke manual Telegram real pendiente
impacto: UI fue compilada, pero no validada dentro de cliente Telegram real
cuando se retoma: hardening/manual QA Telegram
```

```txt
riesgo: warning Starlette/httpx
impacto: no bloquea tests; warning aceptado temporalmente
cuando se retoma: hardening de dependencias de test
```

## Auto-verificacion de Builder

- No toque scope prohibido.
- No cambie reglas de negocio fuera del slice.
- No cambie estados/enums sin contrato.
- No cambie disclaimers prohibidos.
- No expuse secretos.
- No use rutas/endpoints no aprobados.
- No cree tablas fuera del contrato.
- No cree `payment_evidence_files`.
- No cree `storage_objects`.
- No consume creditos.
- No confirme pago del negocio.
- No construi entrega/pago movil.
- No construi chat.
- No construi disputas.
- No deje tests fallando.
- No declare `READY_FOR_REAL_USE`.

## Estado final

```txt
READY_FOR_OWNER_REVIEW
```
