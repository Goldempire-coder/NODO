# Architecture Review - business_intake conversation prompts and validation split

## Estado

PASSED

## Objetivo

Reducir `conversation.py` sin tocar la maquina conversacional del bot. El corte separa copy/prompts y validadores para bajar complejidad antes de mover logica de pasos.

## Corte realizado

Antes:

- `conversation.py` contenia:
  - cliente Telegram
  - prompts/copy
  - botones reply markup
  - validadores de texto/montos/metodos
  - parser de update
  - maquina de pasos
  - submit final

Despues:

- `conversation_prompts.py`
  - `START_BUTTON_TEXTS`
  - `START_REPLY_MARKUP`
  - `REMOVE_REPLY_MARKUP`
  - `STEP_PROMPTS`
- `conversation_validation.py`
  - `validated_amount_range`
  - `clean_text`
  - `split_clean_list`
  - `normalize_operation`
  - `normalize_methods`
- `conversation.py`
  - conserva cliente Telegram, parser de update y flujo conversacional.
- `service.py`
  - ahora importa `validated_amount_range` desde `conversation_validation.py`.

## Archivos modificados

- `apps/api/app/modules/business_intake/conversation.py`
- `apps/api/app/modules/business_intake/conversation_prompts.py`
- `apps/api/app/modules/business_intake/conversation_validation.py`
- `apps/api/app/modules/business_intake/service.py`

## Conteo despues del corte

```txt
conversation.py             452
postgres_repository.py      398
service.py                  291
admin_actions.py            276
memory_repository.py        258
routes.py                   224
telegram_documents.py       181
models.py                    90
repository_common.py         80
conversation_validation.py   59
schemas.py                   45
conversation_prompts.py      33
policy.py                    24
repository.py                 6
```

## Validacion

```txt
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests\test_business_intake_bot.py apps\api\tests\test_telegram_bot_webhook.py -q
22 passed, 1 warning

$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
133 passed, 1 warning

python -m ruff check apps\api scripts
All checks passed

python -m compileall apps\api scripts
OK

corepack pnpm --filter @nodo/web build
OK
```

## Riesgo residual

- `conversation.py` todavia concentra parser de update, manejo de start, idempotencia, documentos y maquina de pasos.
- `telegram_documents.py` mantiene su propio `_clean_text` local para datos de archivos Telegram. No se cambio para evitar mezclar dos cortes.

## Siguiente corte recomendado

Separar cliente Telegram HTTP:

- `telegram_client.py`
  - `telegram_api_post`
  - `telegram_download_file`
  - `telegram_send_message`

Ese corte es seguro porque hoy esas funciones son independientes y ya se monkeypatchean en tests a traves de `service.py`/`routes.py`.
