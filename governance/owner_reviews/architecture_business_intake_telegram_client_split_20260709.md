# Architecture Review - business_intake Telegram client split

## Estado

PASSED

## Objetivo

Separar las llamadas HTTP a Telegram de `conversation.py` sin cambiar el flujo conversacional, los tests existentes, endpoints, payloads, storage, migraciones, frontend ni deploy.

## Corte realizado

Antes:

- `conversation.py` contenia `httpx`, `telegram_api_post`, `telegram_download_file` y `telegram_send_message`.

Despues:

- `telegram_client.py`
  - `telegram_api_post`
  - `telegram_download_file`
  - `telegram_send_message`
- `conversation.py`
  - importa `telegram_download_file` y `telegram_send_message`.
  - conserva la maquina conversacional.
- `service.py` y `routes.py`
  - siguen exponiendo `telegram_send_message`/`telegram_download_file` como antes para no romper monkeypatches de tests.

## Archivos modificados

- `apps/api/app/modules/business_intake/conversation.py`
- `apps/api/app/modules/business_intake/telegram_client.py`

## Conteo despues del corte

```txt
conversation.py             415
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
telegram_client.py           43
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

- `conversation.py` sigue concentrando parsing de update, start/restart, manejo de documentos y maquina de pasos.
- El contrato de tests todavia monkeypatchea `service.py`/`routes.py`; se conservo intencionalmente para evitar cambios de pruebas innecesarios.

## Siguiente corte recomendado

Separar parsing/contexto de Telegram:

- `telegram_update_parser.py`
  - extraer `_telegram_message_context`
  - extraer respuesta vacia si aplica

Este corte reduce la maquina conversacional sin tocar reglas de steps.
