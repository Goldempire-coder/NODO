# Architecture Review - business_intake repository split

## Estado

PASSED

## Objetivo

Separar el repositorio de intake por backend de persistencia sin cambiar imports publicos, endpoints, payloads, reglas del bot, reglas admin, migraciones, frontend ni deploy.

## Corte realizado

Antes:

- `apps/api/app/modules/business_intake/repository.py` mezclaba helpers, repositorio en memoria y repositorio Postgres en 653 lineas.

Despues:

- `apps/api/app/modules/business_intake/repository.py`
  - fachada estable de 6 lineas.
- `apps/api/app/modules/business_intake/memory_repository.py`
  - implementacion in-memory usada en tests.
- `apps/api/app/modules/business_intake/postgres_repository.py`
  - implementacion PostgreSQL usada fuera de test.
- `apps/api/app/modules/business_intake/repository_common.py`
  - conversiones y mappers compartidos.

## Archivos modificados

- `apps/api/app/modules/business_intake/repository.py`
- `apps/api/app/modules/business_intake/memory_repository.py`
- `apps/api/app/modules/business_intake/postgres_repository.py`
- `apps/api/app/modules/business_intake/repository_common.py`

## Conteo despues del corte

```txt
conversation.py         520
postgres_repository.py  398
service.py              291
admin_actions.py        276
memory_repository.py    258
routes.py               224
telegram_documents.py   181
models.py                90
repository_common.py     80
schemas.py               45
policy.py                24
repository.py             6
```

## Import publico preservado

`apps/api/app/main.py` sigue usando:

```txt
from app.modules.business_intake.repository import InMemoryBusinessIntakeRepository, PostgresBusinessIntakeRepository
```

Esto evita cambios de wiring global.

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

- `conversation.py` sigue grande y concentra parser de update, prompts, maquina de pasos, envio Telegram y control de submit.
- `postgres_repository.py` queda en 398 lineas; aceptable por ahora porque es persistencia SQL concentrada.

## Siguiente corte recomendado

Leer `conversation.py` y separar primero constantes/copy/steps a un modulo dedicado. No conviene partir la maquina de estados antes de aislar prompts y normalizadores.
