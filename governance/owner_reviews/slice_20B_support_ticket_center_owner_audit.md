# OWNER AUDIT - slice_20B_support_ticket_center

## Estado

PASSED_AFTER_OWNER_AUDIT_FIX

## Revision realizada

Se revisaron artefactos, modulo backend `support`, migracion `0019`, presenters, routes, service, tests y separacion frontend de superficies.

## Hallazgo corregido

El builder habia implementado `POST /api/v1/admin/support/tickets/{id}/escalate` con `existing_dispute_id`, pero el service solo normalizaba UUID y no validaba:

- que la disputa existiera;
- que perteneciera al mismo `order_id` del ticket cuando el ticket era por orden;
- que perteneciera al mismo negocio cuando el ticket era de negocio;
- que perteneciera al mismo remitter cuando el ticket era de cliente.

Riesgo: un ticket de soporte podia quedar vinculado a una disputa falsa o ajena como contexto.

Fix aplicado:

- `SupportService` ahora recibe `dispute_repository`.
- `escalate` valida la disputa existente antes de guardar `dispute_id`.
- Si la disputa no existe o no pertenece al contexto autorizado, responde `DISPUTE_NOT_FOUND`.
- `attachment_view_url` ahora bloquea con `STORAGE_UNAVAILABLE` si no hay storage configurado.

Archivos corregidos:

- `apps/api/app/modules/support/service.py`
- `apps/api/app/modules/support/routes.py`
- `apps/api/tests/test_support_ticket_center.py`

## Validacion ejecutada

- `python -m pytest apps\api\tests\test_support_ticket_center.py -q --tb=short`: `5 passed, 1 warning`
- `$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q`: `188 passed, 1 warning`
- `python -m ruff check apps\api scripts`: `All checks passed!`
- `python -m compileall apps\api apps\web\src scripts`: OK
- `corepack pnpm --filter @nodo/web build`: OK
- Scan frontend source/build sensible: sin hits.
- Scan dominio soporte: no hay mutaciones de order/ad/credits dentro del modulo `support`.

## Confirmaciones

- No se hizo deploy.
- No se aplicaron migraciones reales.
- No se declaro `READY_FOR_REAL_USE`.
- No se construyo 20C.
- No se cambio lifecycle de ordenes, creditos, anuncios, pagos ni disputas.
