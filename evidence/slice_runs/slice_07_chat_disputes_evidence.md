# slice_07_chat_disputes Evidence

Fecha: 2026-07-04

Estado: READY_FOR_OWNER_REVIEW

## Scope verificado

- Chat entre remitter y business owner sobre orden propia.
- Attachments privados de mensaje via `file_assets` y storage privado.
- Apertura de disputas sin resolucion admin.
- Listado/detalle read-only de disputas para admin/support/super_admin.
- UI gobernada para `R-09_ORDER_TRACKING_CHAT` y `B-13_BUSINESS_CHAT`.
- No se construyo `R-10_CONFIRM_RECEIVED`, completion, rating, auto-complete, ni resolucion admin.

## Evidencia backend

- `GET /api/v1/orders/{id}/messages` implementado y probado.
- `POST /api/v1/orders/{id}/messages` implementado y probado con idempotencia.
- `POST /api/v1/orders/{id}/message-attachments` implementado y probado con MIME/size/private metadata.
- `POST /api/v1/orders/{id}/disputes` implementado y probado con idempotencia.
- `GET /api/v1/admin/disputes` implementado read-only.
- `GET /api/v1/admin/disputes/{id}` implementado read-only.
- `POST /api/v1/admin/disputes/{id}/resolve` no existe; prueba devuelve 404.

## Evidencia data/migraciones

- Migracion `0008_slice_07_chat_disputes.up.sql` crea:
  - `messages`
  - `message_attachments`
  - `disputes`
  - `dispute_events`
- Migracion reversible `0008_slice_07_chat_disputes.down.sql` incluida.
- `file_assets` se amplia para `resource_type = message` y `file_type = message_attachment`.
- No se creo `chat_messages`.

## Evidencia seguridad

- Ownership de chat/disputa probado para remitter, business owner y actor externo.
- Admin/support solo lectura en disputas.
- Attachments no exponen ruta interna.
- Escaneo frontend source/build sin hits para secretos, `storage_path`, `account_value`, rutas prohibidas ni copy prohibida.
- Audit events probados:
  - `message_created`
  - `message_attachment_uploaded`
  - `dispute_opened`
  - `dispute_message_created`
- `message_sent` y `dispute_resolved` no se emiten por slice 07.

## Comandos ejecutados

```txt
corepack pnpm --filter @nodo/web build
Resultado: OK
```

```txt
python scripts\run_slice_00_tests.py
Resultado: 6 passed, 0 failed
```

```txt
python scripts\run_slice_01_tests.py
Resultado: 6 passed, 0 failed
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
```

```txt
python scripts\run_slice_05_tests.py
Resultado: OK
```

```txt
python scripts\run_slice_06_tests.py
Resultado: OK
```

```txt
python scripts\run_slice_07_tests.py
Resultado: OK, 7 passed, 1 warning
```

```txt
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
Resultado: 64 passed, 1 warning
```

```txt
python -m ruff check apps\api scripts
Resultado: OK
```

```txt
python -m compileall apps scripts
Resultado: OK
```

```txt
frontend source/build private-data scan
Resultado: OK
```

## Resultados JSON

- `evidence/slice_runs/slice_07_chat_disputes_test_results.json`

## Riesgos residuales heredados

- Migraciones reales contra PostgreSQL/Supabase pendientes.
- Redis real pendiente.
- Storage privado real pendiente.
- Smoke manual Telegram real pendiente.
- Warning Starlette/httpx aceptado temporalmente.
- Compra/acreditacion real de creditos queda para slice_08.
- Runtime Postgres debe usar Jsonb/adaptadores seguros para columnas jsonb.
- IDs de entrada que van a columnas UUID deben validarse antes de tocar Postgres.

## Scope no construido

- Resolucion admin de disputas.
- `POST /api/v1/admin/disputes/{id}/resolve`.
- `R-10_CONFIRM_RECEIVED`.
- Completion, rating, auto-complete.
- Jobs masivos.
- Movimientos de creditos por resolucion de disputa.
- Admin UI de disputas.
- Slice 08.
