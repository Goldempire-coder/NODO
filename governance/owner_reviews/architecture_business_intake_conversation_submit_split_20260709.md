# Architecture Review - business_intake conversation submit split

## Estado

PASSED

## Objetivo

Separar la validacion del submit final del bot de `conversation.py` sin tocar start/restart, documentos, orden de pasos, endpoints, payloads, storage, migraciones, frontend ni deploy.

## Corte realizado

Antes:

- `conversation.py` contenia:
  - palabras finales permitidas: `finalizar`, `terminar`, `enviar`, `submit`, `done`
  - verificacion de datos minimos
  - verificacion de documentos antes de submit

Despues:

- `conversation_submit.py`
  - `SUBMIT_WORDS`
  - `ensure_submit_command`
  - `ensure_ready_to_submit`
- `conversation.py`
  - mantiene `_handle_submit_text`, persistencia, audit y envio de confirmacion.

## Archivos modificados

- `apps/api/app/modules/business_intake/conversation.py`
- `apps/api/app/modules/business_intake/conversation_submit.py`

## Conteo despues del corte

```txt
postgres_repository.py      398
conversation.py             322
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
conversation_submit.py       24
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

- `conversation.py` todavia contiene start/restart, idempotencia, contacto, documentos y persistencia del submit.
- Esa parte ya es el nucleo del flujo Telegram; partirla mas requiere pruebas reales adicionales del bot para evitar regresiones silenciosas.

## Recomendacion

Parar cortes dentro de `business_intake/conversation.py` por ahora. El archivo bajo a 322 lineas y ya no contiene HTTP, prompts, validadores, parser, mapeo de pasos ni validacion de submit final.

La siguiente mejora de arquitectura deberia ir a otro modulo grande o a pruebas reales del bot antes de tocar start/restart.
