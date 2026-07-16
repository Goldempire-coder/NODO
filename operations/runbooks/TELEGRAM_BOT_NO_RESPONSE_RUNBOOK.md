# RUNBOOK: Telegram bot does not respond

Estado de validacion: PARTIALLY VALIDATED

## SINTOMA

Usuario escribe `/start` o usa boton y bot no responde.

## SEVERIDAD INICIAL

SEV-2 si afecta entrada cliente/negocio.

## PRIMEROS CINCO MINUTOS

1. Confirmar API `/ready`.
2. Ejecutar reject-only smoke:
   ```powershell
   python scripts\staging_telegram_webhook_smoke.py --env-file .local\staging_validation_17C_LOCAL_ONLY.env --bot business-intake --output evidence\slice_runs\telegram_reject_<timestamp>.json
   ```
3. Revisar que token correcto este en Railway, no en frontend.

## DIAGNOSTICO

- Bot cliente usa `BOT_TOKEN`.
- Bot negocio usa `BUSINESS_INTAKE_BOT_TOKEN`.
- Webhooks separados:
  - `/api/v1/telegram/webhook/{secret}`
  - `/api/v1/business-intake/telegram/webhook/{secret}`

## MITIGACION

- Corregir env o webhook provider.
- No mezclar tokens.

## PROHIBICIONES

- No imprimir token.
- No mandar mensajes de prueba a usuarios reales.
