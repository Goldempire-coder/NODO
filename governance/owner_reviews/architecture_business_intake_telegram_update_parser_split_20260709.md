# Architecture Review - business_intake Telegram update parser split

## Estado

PASSED

## Objetivo

Separar el parsing de updates Telegram de `conversation.py` sin tocar la maquina de pasos, endpoints, payloads, storage, migraciones, frontend ni deploy.

## Corte realizado

Antes:

- `conversation.py` contenia:
  - `_empty_telegram_response`
  - `_telegram_message_context`
  - maquina conversacional

Despues:

- `telegram_update_parser.py`
  - `empty_telegram_response`
  - `telegram_message_context`
- `conversation.py`
  - importa esas funciones y mantiene el flujo conversacional.

## Archivos modificados

- `apps/api/app/modules/business_intake/conversation.py`
- `apps/api/app/modules/business_intake/telegram_update_parser.py`

## Conteo despues del corte

```txt
postgres_repository.py      398
conversation.py             390
service.py                  291
admin_actions.py            276
memory_repository.py        258
routes.py                   224
telegram_documents.py       181
models.py                    90
repository_common.py         80
conversation_validation.py   59
schemas.py                   45
telegram_client.py           43
telegram_update_parser.py    40
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

- `conversation.py` todavia contiene start/restart, idempotencia, contacto, documentos, steps y submit.
- `routes.py` mantiene su propio parser simple para recuperar errores; no se toco porque devuelve una tupla distinta y se usa en otra capa.

## Siguiente corte recomendado

Separar el mapeo de respuestas por step:

- `conversation_steps.py`
  - extraer `_conversation_fields_for_step`
  - mantener `_handle_text_step` en `conversation.py`

Ese corte toca la maquina de pasos, pero sigue siendo razonablemente acotado si se valida completo.
