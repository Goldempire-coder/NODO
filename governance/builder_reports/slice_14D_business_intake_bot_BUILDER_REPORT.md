# BUILDER_REPORT - slice_14D_business_intake_bot

## Estado final
READY_FOR_OWNER_REVIEW

## Resumen
Se construyo el Bot Registro Negocios como superficie backend separada para intake de negocios interesados. El slice crea solicitudes revisables, captura contacto y datos del negocio, acepta documentos privados con `file_assets`, expone cola admin para revisar solicitudes y mantiene auditoria.

El bot/intake no crea negocios activos, no cambia roles, no crea `business_access_links`, no da acceso a Mini App Negocio, no crea anuncios y no acredita creditos.

## Archivos modificados
- `apps/api/app/main.py`
- `apps/api/app/core/config.py`
- `apps/api/app/core/errors.py`
- `apps/api/app/routes/telegram_bot.py`
- `apps/api/app/shared/storage/private.py`
- `apps/api/app/modules/business_intake/__init__.py`
- `apps/api/app/modules/business_intake/models.py`
- `apps/api/app/modules/business_intake/policy.py`
- `apps/api/app/modules/business_intake/repository.py`
- `apps/api/app/modules/business_intake/routes.py`
- `apps/api/app/modules/business_intake/schemas.py`
- `apps/api/app/modules/business_intake/service.py`
- `apps/api/tests/test_business_intake_bot.py`
- `database/migrations/0014_slice_14D_business_intake_bot.up.sql`
- `database/migrations/0014_slice_14D_business_intake_bot.down.sql`
- `scripts/run_slice_14D_tests.py`
- `evidence/slice_runs/slice_14D_business_intake_bot_evidence.md`
- `evidence/slice_runs/slice_14D_business_intake_bot_test_results.json`

## Migraciones creadas
- `0014_slice_14D_business_intake_bot.up.sql`
- `0014_slice_14D_business_intake_bot.down.sql`

La migracion crea `business_intake_requests`, agrega soporte de `file_assets.resource_type = business_intake`, `file_assets.file_type = intake_document`, `metadata_json` para metadatos del documento, constraints e indices de consulta/idempotencia.

## Endpoints construidos
- `POST /api/v1/business-intake/start`
- `POST /api/v1/business-intake/{id}/contact`
- `POST /api/v1/business-intake/{id}/submit`
- `POST /api/v1/business-intake/{id}/documents`
- `GET /api/v1/admin/business-intake`
- `GET /api/v1/admin/business-intake/{id}`
- `POST /api/v1/admin/business-intake/{id}/accept`
- `POST /api/v1/admin/business-intake/{id}/reject`

Tambien se extendio `POST /api/v1/telegram/webhook/{secret}` para manejar `/start negocio` y contacto compartido sin romper `/start` existente.

## Seguridad y alcance
- Contacto compartido valida `contact_user_id == telegram_user_id`.
- Idempotencia Telegram por `telegram_chat_id + last_update_id`.
- Admin accept/reject requiere RBAC, `reason` e `Idempotency-Key`.
- Support puede leer, pero no aceptar/rechazar.
- Documentos usan storage privado y `file_assets`; la API publica no devuelve `storage_path`.
- Videos y MIME no permitidos devuelven `BOT_UPLOAD_INVALID`.
- Tamano maximo: 5 MB.
- No se exponen secretos, tokens, `account_value` ni datos bancarios completos.

## Pruebas ejecutadas
- `python scripts\run_slice_14D_tests.py`: passed
  - `7 passed, 1 warning in 2.04s`
  - ruff focalizado: `All checks passed!`
  - compileall focalizado: passed
- `$env:PYTHONPATH='apps/api;C:\Users\carlo\AppData\Roaming\Python\Python314\site-packages'; python -m pytest apps\api\tests -q`: `117 passed, 1 warning in 23.38s`
- `corepack pnpm --filter @nodo/web build`: passed
- `python -m ruff check apps\api scripts`: `All checks passed!`
- `python -m compileall apps scripts`: passed
- Frontend/source scan: sin hits para `BOT_TOKEN`, `SUPABASE_SERVICE_ROLE_KEY`, `JWT_SECRET`, `JWT_REFRESH_SECRET`, `storage_path`, `account_value` ni claims prohibidos.
- Public API slice scan: `schemas.py`, `routes.py` y `telegram_bot.py` sin `storage_path` ni `account_value`.

## Evidencia
- `evidence/slice_runs/slice_14D_business_intake_bot_evidence.md`
- `evidence/slice_runs/slice_14D_business_intake_bot_test_results.json`

## Riesgos residuales
- El webhook conversacional implementa entrada `/start negocio` y contacto compartido; el submit completo y documentos quedan servidos por endpoints bot protegidos para ser orquestados por el flujo/bot. No se hizo smoke real contra Telegram.
- Storage privado real sigue dependiendo de configuracion runtime, como en riesgos heredados.
- Warning Starlette/httpx permanece aceptado temporalmente.

## Confirmaciones
- No hice deploy.
- No declare READY_FOR_REAL_USE.
- No cree negocio activo.
- No cree `business_access_links`.
- No cambie roles a `business_owner`.
- No di acceso a Mini App Negocio.
- No cree anuncios.
- No acredite creditos.
- No toque Mini App Cliente, Mini App Negocio ni Admin Web.
