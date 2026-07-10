# Architecture Review - business_intake admin actions split

## Estado

PASSED

## Objetivo

Reducir el acoplamiento de `BusinessIntakeService` sin cambiar endpoints, payloads, reglas de negocio, bot flow, admin behavior, migraciones, frontend ni deploy.

## Corte realizado

Se extrajeron las acciones admin de intake a:

- `apps/api/app/modules/business_intake/admin_actions.py`

`BusinessIntakeService` queda enfocado en:

- inicio/contacto/submit de intake
- upload de documentos
- delegacion del webhook conversacional
- serializacion publica del intake/documentos

`BusinessIntakeAdminActions` queda responsable de:

- listar solicitudes admin
- ver detalle admin
- aceptar/rechazar solicitudes
- borrar registro de intake
- crear negocio desde intake cuando el admin lo solicita
- auditoria admin e idempotencia de acciones admin

## Archivos modificados

- `apps/api/app/modules/business_intake/service.py`
- `apps/api/app/modules/business_intake/admin_actions.py`

## Conteo despues del corte

```txt
repository.py          653
conversation.py        520
service.py             291
admin_actions.py       276
routes.py              224
telegram_documents.py  181
models.py               90
schemas.py              45
policy.py               24
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

- `repository.py` sigue mezclando memoria y Postgres.
- `conversation.py` sigue siendo grande y concentra maquina de pasos, prompts, manejo de updates y control del flujo conversacional.

## Siguiente corte recomendado

Antes de tocar comportamiento del bot, dividir `repository.py` en repositorios por backend:

- `memory_repository.py`
- `postgres_repository.py`
- `repository.py` como facade/export estable o modulo de helpers compartidos

Ese corte reduce tamano sin cambiar reglas del bot.
