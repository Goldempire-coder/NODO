# RUNBOOK: Secrets compromised or lost

Estado de validacion: NOT VALIDATED
Ultima actualizacion: 2026-07-11

## Sintoma

- Secret filtrado.
- Secret perdido.
- Backend no arranca por env faltante.
- Bot/storage/RPC/JWT deja de funcionar tras restore o deploy.

## Severidad inicial

SEV-1 para JWT, DB, Redis, Supabase service role, bot token, Base RPC key o storage key.

## Primeros cinco minutos

1. No imprimir el secreto.
2. Identificar entorno y proveedor.
3. Congelar deploys si puede empeorar.
4. Usar `SECRETS_RECOVERY_SOP.md`.

## Diagnostico

- Revisar presencia/ausencia en provider sin mostrar valor.
- Ejecutar health/ready/version despues de correccion.
- Smoke especifico si aplica: Telegram, storage, Base RPC.

## Recuperacion

Rotacion o reconfiguracion segun provider. COMMAND NOT AVAILABLE en repo.

## Prohibiciones

- No pegar secrets en chat, logs, evidencia o screenshots.
- No colocar backend secrets en Cloudflare Pages.
- No rotar JWT sin plan de re-auth/logout.
