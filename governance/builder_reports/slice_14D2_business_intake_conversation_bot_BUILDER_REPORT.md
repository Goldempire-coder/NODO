# BUILDER_REPORT - slice_14D2_business_intake_conversation_bot

## Estado final
READY_FOR_OWNER_REVIEW

## Resumen
Se construyo el bot conversacional separado para intake de negocios usando `BUSINESS_INTAKE_BOT_TOKEN` y el webhook canonico `POST /api/v1/business-intake/telegram/webhook/{secret}`. El flujo captura contacto, datos del negocio, documentos permitidos y submit final, sin crear negocio activo, sin cambiar roles y sin crear `business_access_links`.

## Archivos modificados
- `apps/api/app/core/config.py`
- `apps/api/app/core/errors.py`
- `apps/api/app/modules/business_intake/models.py`
- `apps/api/app/modules/business_intake/repository.py`
- `apps/api/app/modules/business_intake/service.py`
- `apps/api/app/modules/business_intake/routes.py`
- `apps/api/app/routes/telegram_bot.py`
- `apps/api/tests/test_business_intake_bot.py`
- `apps/api/tests/test_telegram_bot_webhook.py`

## Artefactos creados
- `governance/builder_reports/slice_14D2_business_intake_conversation_bot_BUILDER_REPORT.md`
- `evidence/slice_runs/slice_14D2_business_intake_conversation_bot_evidence.md`
- `evidence/slice_runs/slice_14D2_business_intake_conversation_bot_test_results.json`

## Endpoints construidos o ajustados
- Construido: `POST /api/v1/business-intake/telegram/webhook/{secret}`
- Ajustado: `POST /api/v1/telegram/webhook/{secret}` para no procesar intake de negocio en el bot cliente.

## Que se construyo
- Configuracion `BUSINESS_INTAKE_BOT_TOKEN`.
- Validacion de secret separada para el bot de intake.
- Conversacion paso a paso:
  - `/start`
  - `awaiting_contact`
  - `awaiting_business_name`
  - `awaiting_responsible_name`
  - `awaiting_city`
  - `awaiting_business_phone`
  - `awaiting_operation`
  - `awaiting_banks`
  - `awaiting_methods`
  - `awaiting_min_amount`
  - `awaiting_max_amount`
  - `awaiting_schedule`
  - `awaiting_references`
  - `awaiting_documents`
  - `submitted`
- Persistencia parcial por paso en `business_intake_requests`.
- Validacion de contacto Telegram: `contact.user_id == telegram_user_id`.
- Idempotencia por `telegram_chat_id + update_id`.
- Descarga de documentos desde Telegram y guardado privado via `file_assets`.
- Dedupe de documentos por metadata de Telegram.
- Rechazo de video/audio/MIME invalido/archivo mayor a 5 MB con `BOT_UPLOAD_INVALID`.
- Audit events existentes del intake.

## Que NO se construyo
- No se creo negocio activo.
- No se creo `business_access_links`.
- No se cambio `users.role`.
- No se dio acceso a Mini App Negocio.
- No se construyo Mini App Cliente.
- No se construyo Mini App Negocio.
- No se construyo Admin Web.
- No se crearon anuncios.
- No se tocaron creditos.
- No se hizo deploy.
- No se declaro `READY_FOR_REAL_USE`.

## Migraciones
No se creo migracion. El schema de slice 14D ya cubre `business_intake_requests`, `last_step`, `last_update_id`, `telegram_user_id`, `telegram_chat_id` y `file_assets`. Los metadatos de archivo Telegram se guardan en `metadata_json`.

## Validaciones ejecutadas
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_business_intake_bot.py apps\api\tests\test_telegram_bot_webhook.py -q`
  - `17 passed, 1 warning in 4.19s`
- `corepack pnpm --filter @nodo/web build`
  - OK
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`
  - `124 passed, 1 warning in 31.89s`
- `python -m ruff check apps\api scripts`
  - `All checks passed!`
- `python -m compileall apps scripts`
  - OK

## Scans ejecutados
- Frontend source/build scan de secrets/datos privados/claims prohibidos:
  - Resultado: sin matches.
- Backend intake scan:
  - Resultado: solo matches esperados en config, tests, storage interno y assertions de no exposicion.

## Riesgos residuales
- Queda pendiente smoke real de Telegram/Railway con webhook configurado; no se hizo deploy por alcance.
- Storage privado real depende del adapter configurado en runtime.
- Warning Starlette/httpx existente se mantiene como riesgo aceptado temporalmente.

## Confirmaciones
- No modifique frontend de producto.
- No modifique migraciones.
- No instale dependencias.
- No hice deploy.
- No cree negocio activo.
- No cree `business_access_links`.
- No cambie roles.
- No di acceso a Mini App Negocio.
- No declare `READY_FOR_REAL_USE`.
