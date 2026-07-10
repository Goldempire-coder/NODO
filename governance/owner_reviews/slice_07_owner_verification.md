# OWNER VERIFICATION - slice_07_chat_disputes

Estado final: OWNER_ACCEPTED_FOR_NEXT_SLICE

Fecha: 2026-07-04

## Resultado

`slice_07_chat_disputes` queda aceptado para avanzar al siguiente slice, con correcciones aplicadas durante owner review.

No se declara `READY_FOR_REAL_USE`.

## Auditoria realizada

Se revisaron:

- `governance/builder_reports/slice_07_chat_disputes_BUILDER_REPORT.md`
- `evidence/slice_runs/slice_07_chat_disputes_evidence.md`
- `evidence/slice_runs/slice_07_chat_disputes_test_results.json`
- `apps/api/app/modules/chat/routes.py`
- `apps/api/app/modules/chat/service.py`
- `apps/api/app/modules/chat/repository.py`
- `apps/api/app/modules/chat/policy.py`
- `apps/api/app/modules/disputes/routes.py`
- `apps/api/app/modules/disputes/service.py`
- `apps/api/app/modules/disputes/repository.py`
- `apps/api/app/modules/disputes/policy.py`
- `apps/api/tests/test_chat_disputes.py`
- `database/migrations/0008_slice_07_chat_disputes.up.sql`
- `database/migrations/0008_slice_07_chat_disputes.down.sql`
- `apps/web/src/app/page.tsx`

## Hallazgos corregidos

### 1. Migracion no alineada al contrato

La migracion `0008_slice_07_chat_disputes.up.sql` tenia diferencias contra `DATA_CONTRACT.md` y `ENUMS_AND_STATUS_MASTER.md`:

- `messages.visibility` permitia `admin`, pero el contrato usa `admin_only`.
- `messages.status` omitía `hidden`.
- `dispute_events.event_type` omitía eventos reservados futuros del contrato.
- `disputes` incluia columna `resolution`, no definida en el contrato.

Correccion:

- `messages_visibility_check` ahora usa `('parties', 'admin_only')`.
- `messages_status_check` ahora usa `('visible', 'hidden', 'deleted')`.
- `dispute_events_event_type_check` incluye eventos reservados futuros.
- Se elimino la columna/campo `resolution`.
- Se actualizaron `DisputeRecord`, `PostgresDisputeRepository` y tests.

### 2. Evidence ids de disputa no se validaban

`open_dispute` normalizaba `evidence_file_ids` como UUID, pero no validaba que los adjuntos existieran, pertenecieran a la misma orden ni hubieran sido subidos por el actor.

Riesgo:

- Una disputa podia referenciar evidencia inexistente o ajena en metadata.

Correccion:

- `DisputeService` ahora recibe `chat_repository`.
- Cada `evidence_file_id` debe existir como attachment.
- El attachment debe pertenecer a la misma orden.
- El attachment debe haber sido subido por el actor que abre la disputa.
- Si falla, responde `MESSAGE_ATTACHMENT_INVALID`.
- Se agrego cobertura en `test_chat_disputes.py`.

## Contratos validados

- Tabla canonica `messages`; no `chat_messages`.
- Chat disponible solo para participantes autorizados y admin/support read-only segun RBAC.
- Adjuntos usan storage privado y no exponen `storage_path`.
- Apertura de disputa cambia `orders.status = disputed` y guarda `previous_order_status`.
- Disputa desde `payment_reported/payment_rejected` mantiene creditos bloqueados y `ad.status = in_order`.
- Disputa desde `payment_confirmed/delivered` mantiene creditos consumidos y `ad.status = archived`.
- Admin/super_admin/support solo tienen vista read-only de disputas.
- No existe endpoint de resolucion admin en slice 07.
- `dispute_resolved` queda reservado para futuro y no se emite en slice 07.

## Scope prohibido no construido

- Resolucion admin de disputas.
- `POST /api/v1/admin/disputes/{id}/resolve`.
- `R-10_CONFIRM_RECEIVED`.
- Completion.
- Rating.
- Auto-complete.
- Jobs masivos.
- Movimientos de creditos por resolucion de disputa.
- Admin UI A-06/A-07.
- Slice 08.

## Verificacion ejecutada

- `corepack pnpm --filter @nodo/web build` -> OK
- `python scripts\run_slice_00_tests.py` -> OK, 6 passed
- `python scripts\run_slice_01_tests.py` -> OK, 6 passed
- `python scripts\run_slice_02_tests.py` -> OK
- `python scripts\run_slice_03_tests.py` -> OK
- `python scripts\run_slice_04_tests.py` -> OK
- `python scripts\run_slice_05_tests.py` -> OK
- `python scripts\run_slice_06_tests.py` -> OK
- `python scripts\run_slice_07_tests.py` -> OK
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q` -> OK, 64 passed, 1 warning
- `python -m ruff check apps\api scripts` -> OK
- `python -m compileall apps scripts` -> OK
- Source scan acotado -> sin exposicion en frontend/app responses; hits restantes son usos internos o assertions de tests.

## Riesgos residuales

- Migraciones reales contra PostgreSQL/Supabase siguen pendientes.
- Redis real sigue pendiente.
- Storage privado real sigue pendiente.
- Smoke Telegram real sigue pendiente.
- Warning Starlette/httpx sigue aceptado temporalmente.

## Estado

`slice_07_chat_disputes = OWNER_ACCEPTED_FOR_NEXT_SLICE`

