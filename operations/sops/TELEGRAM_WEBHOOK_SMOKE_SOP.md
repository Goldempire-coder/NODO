# SOP: Telegram Webhook Smoke

SOP_ID: SOP-TELEGRAM-001
Estado de validacion: PARTIALLY VALIDATED

## Reject-only seguro

```powershell
python scripts\staging_telegram_webhook_smoke.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --bot business-intake --output evidence\slice_runs\telegram_reject_<timestamp>.json
```

Resultado esperado: secret invalido devuelve 403.

## Valid test chat

Solo con chat de prueba autorizado:

```powershell
python scripts\staging_telegram_webhook_smoke.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --bot business-intake --allow-send --test-chat-id <TEST_CHAT_ID> --output evidence\slice_runs\telegram_valid_<timestamp>.json
```

## Prohibiciones

- No imprimir BOT_TOKEN.
- No usar token cliente para bot negocio.
- No usar chat real de cliente sin permiso.
