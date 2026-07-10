# OWNER AUDIT - slice_14D2_business_intake_conversation_bot

Estado final: `PASSED_AFTER_OWNER_AUDIT_FIX`

Fecha: 2026-07-08

## Resultado

El builder entrego `READY_FOR_OWNER_REVIEW`, pero la auditoria no lo acepto directamente.

Se encontro y corrigio un bug real de robustez conversacional:

1. Un retry viejo de Telegram despues de avanzar de paso devolvia `400 BOT_INPUT_INVALID` en vez de ser un no-op seguro.
2. Despues de `submitted`, un mensaje nuevo podia crear otro draft porque el webhook solo buscaba drafts activos.

Ambos casos podian causar ruido, retries y solicitudes duplicadas en uso real.

## Correccion aplicada

Archivos modificados por auditoria:

- `apps/api/app/modules/business_intake/repository.py`
- `apps/api/app/modules/business_intake/service.py`
- `apps/api/tests/test_business_intake_bot.py`

Cambios principales:

- Agregado `get_latest_for_chat` en repositorio in-memory y Postgres.
- El webhook ahora detecta el ultimo intake del chat.
- Si llega un update viejo con `update_id <= last_update_id`, responde `200` como `duplicate_update`.
- Si el intake ya esta `submitted`, `accepted` o `rejected`, un mensaje nuevo no crea otro draft.
- Se agregaron pruebas especificas para ambos bordes.

Referencias:

- `apps/api/app/modules/business_intake/repository.py:110`
- `apps/api/app/modules/business_intake/repository.py:310`
- `apps/api/app/modules/business_intake/service.py:230`
- `apps/api/app/modules/business_intake/service.py:251`
- `apps/api/tests/test_business_intake_bot.py:577`
- `apps/api/tests/test_business_intake_bot.py:608`

## Validaciones ejecutadas

```txt
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_business_intake_bot.py apps\api\tests\test_telegram_bot_webhook.py -q
19 passed, 1 warning
```

```txt
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
126 passed, 1 warning
```

```txt
python -m ruff check apps\api scripts
All checks passed
```

```txt
python -m compileall apps scripts
passed
```

```txt
corepack pnpm --filter @nodo/web build
passed
```

```txt
rg frontend secret/private scan
0 matches
```

## Confirmaciones

- No se creo negocio activo.
- No se creo `business_access_links`.
- No se cambiaron roles a `business_owner`.
- No se dio acceso a Mini App Negocio.
- No se hizo deploy.
- No se declaro `READY_FOR_REAL_USE`.

## Riesgo residual

- Falta configurar el webhook real del Bot Registro Negocios contra Railway.
- Falta smoke real desde Telegram con `BUSINESS_INTAKE_BOT_TOKEN`.
- Falta smoke real de descarga de documentos contra Telegram + Supabase Storage.
- Warning Starlette/httpx sigue aceptado temporalmente.

