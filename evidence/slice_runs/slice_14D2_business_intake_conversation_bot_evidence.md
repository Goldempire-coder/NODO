# Evidence - slice_14D2_business_intake_conversation_bot

Estado final: READY_FOR_OWNER_REVIEW

## Implementacion verificada
- Se agrego configuracion backend para `BUSINESS_INTAKE_BOT_TOKEN`.
- Se agrego webhook separado `POST /api/v1/business-intake/telegram/webhook/{secret}`.
- El webhook de intake valida secret derivado de `BUSINESS_INTAKE_BOT_TOKEN`.
- El webhook cliente `POST /api/v1/telegram/webhook/{secret}` rechaza el secret del bot de negocios.
- El bot cliente ya no procesa `/start negocio` ni contacto como intake.
- El flujo conversacional persiste parcialmente cada paso canonico.
- La confirmacion final enviada es: `Solicitud recibida. Revisaremos tu informacion y te avisaremos el siguiente paso.`
- El bot descarga documentos desde Telegram mediante el token del bot de intake y los guarda como documentos privados de `business_intake`.
- Se rechazan video/audio/MIME invalido/archivo mayor a 5 MB con `BOT_UPLOAD_INVALID`.
- La idempotencia por `telegram_chat_id + update_id` evita duplicar solicitudes y documentos.

## Evidencia de no scope prohibido
- Tests confirman que el bot no crea `businesses`.
- Tests confirman que el bot no crea `business_access_links`.
- Tests confirman que el bot no cambia `users.role`.
- No se implemento deploy.
- No se construyo Mini App Cliente, Mini App Negocio ni Admin Web.
- No se agregaron anuncios, creditos ni acceso a Mini App Negocio.

## Comandos ejecutados
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_business_intake_bot.py apps\api\tests\test_telegram_bot_webhook.py -q`
  - Resultado: `17 passed, 1 warning in 4.19s`
- `corepack pnpm --filter @nodo/web build`
  - Resultado: OK
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`
  - Resultado: `124 passed, 1 warning in 31.89s`
- `python -m ruff check apps\api scripts`
  - Resultado: `All checks passed!`
- `python -m compileall apps scripts`
  - Resultado: OK

## Scans
- Frontend source/build scan:
  - Comando: `rg -n "BUSINESS_INTAKE_BOT_TOKEN|BOT_TOKEN|SUPABASE_SERVICE_ROLE_KEY|JWT_SECRET|storage_path|account_value|escrow|fondos protegidos|pago garantizado|garant[ií]a de entrega|NODO recibi[oó] dinero" apps\web\src apps\web\.next apps\web\out`
  - Resultado: sin matches.
- Backend intake scan:
  - Comando: `rg -n "BUSINESS_INTAKE_BOT_TOKEN|BOT_TOKEN|storage_path|account_value" apps\api\app\modules\business_intake apps\api\app\routes\telegram_bot.py apps\api\app\core\config.py apps\api\tests\test_business_intake_bot.py apps\api\tests\test_telegram_bot_webhook.py`
  - Resultado: matches esperados en config, tests, storage interno y assertions de no exposicion.

## Riesgos residuales
- Descarga real desde Telegram queda pendiente de smoke con webhook real; en esta fase se valido con mocks.
- Storage privado depende del adapter configurado en runtime.
