# Architecture Review - business_intake conversation steps split

## Estado

PASSED

## Objetivo

Separar el mapeo de respuestas por paso de `conversation.py` sin cambiar orden de preguntas, estados, validaciones, auditoria, endpoints, storage, migraciones, frontend ni deploy.

## Corte realizado

Antes:

- `conversation.py` contenia `_conversation_fields_for_step`, con:
  - asignacion de campos por step
  - proximo step
  - validacion de montos/metodos/listas

Despues:

- `conversation_steps.py`
  - `conversation_fields_for_step`
- `conversation.py`
  - mantiene `_handle_text_step`, audit, persistencia y envio del siguiente prompt.

## Archivos modificados

- `apps/api/app/modules/business_intake/conversation.py`
- `apps/api/app/modules/business_intake/conversation_steps.py`

## Conteo despues del corte

```txt
postgres_repository.py      398
conversation.py             328
service.py                  291
admin_actions.py            276
memory_repository.py        258
routes.py                   224
telegram_documents.py       181
models.py                    90
repository_common.py         80
conversation_steps.py        70
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

- `conversation.py` todavia concentra start/restart, idempotencia, contacto, documentos y submit final.
- `postgres_repository.py` queda grande, pero esta concentrado en persistencia SQL.

## Siguiente corte recomendado

Parar aqui dentro de `business_intake` o hacer un corte menor adicional:

- `conversation_submit.py`
  - extraer validacion de palabras finales y `_ensure_ready_to_submit`

No recomiendo separar start/restart todavia sin pruebas adicionales de flujo real Telegram, porque ahi vive la mayor fragilidad operativa.
