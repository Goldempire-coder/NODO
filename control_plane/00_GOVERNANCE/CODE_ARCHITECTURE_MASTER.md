# CODE_ARCHITECTURE_MASTER.md

## Slice 14 - Arquitectura de superficies

La arquitectura futura debe separar shells por superficie:
- `client-miniapp`: Mini App Cliente.
- `business-miniapp`: Mini App Negocio.
- `admin-web`: Panel Admin Web Desktop.
- `bot`: Bot Registro Negocios.
- `api`: backend unico compartido.

Los paquetes/shells frontend no deben importar pantallas de otra superficie salvo componentes compartidos neutrales.

El backend conserva modulos compartidos y separa routes/schemas/services/repositories/policies por dominio.

No se permite que una pantalla de cliente ejecute handlers de negocio/admin por conveniencia. No se permite que admin web dependa de Telegram MainButton como control principal.

Este documento define la arquitectura de codigo obligatoria para NODO.

## Principio

NODO debe construirse como software profesional, modular, testeable y mantenible.

La UI no decide permisos. El backend valida identidad, rol, recurso, estado y accion.

## Estructura obligatoria

```txt
NODO/
  apps/
    web/
      src/
        app/
        screens/
          remitter/
          business/
          admin/
        components/
          common/
          forms/
          feedback/
          layout/
          order/
          business/
          admin/
        hooks/
        api/
        state/
        theme/
        utils/
        lib/
        types/

    api/
      app/
        main.py
        core/
          config.py
          security.py
          errors.py
          logging.py
        auth/
          telegram.py
          jwt.py
          dependencies.py
        modules/
          users/
            routes.py
            service.py
            repository.py
            schemas.py
            tests/
          businesses/
          payment_methods/
          ads/
          orders/
            routes.py
            service.py
            repository.py
            schemas.py
            state_machine.py
            tests/
          payment_reports/
          chat/
          credits/
          referrals/
          ratings/
          disputes/
          notifications/
          admin/
        shared/
          audit/
          storage/
          validators/
          rate_limit/
          permissions/
          pagination/
          time/
        jobs/
          expire_orders.py
          send_notifications.py
          cleanup_uploads.py
          recalc_metrics.py

    bot/
      app/
        main.py
        handlers/
        services/
        keyboards/
        notifications/

  database/
    migrations/
    seeds/
    schema_docs/

  control_plane/
  tests/
    e2e/
    load/
    security/
```

## Backend responsibilities

routes.py:
- parse request
- apply auth dependency
- call service
- return response
- no business logic
- no raw SQL
- no state transitions

service.py:
- coordinate business logic
- call repositories
- call state machines
- call audit helpers
- enqueue notifications/jobs

repository.py:
- contains DB queries only
- does not decide business rules
- does not write audit events

schemas.py:
- validates input and output
- exposes typed request/response contracts

state_machine.py:
- owns allowed transitions
- rejects invalid transitions
- returns human-safe errors

shared/permissions:
- checks actor, resource ownership, role and status
- no UI permission decisions

shared/audit:
- writes audit events
- no business logic

jobs:
- async work only
- expiration, notifications, cleanup, metrics
- idempotent by design

## Frontend responsibilities

screens:
- render screen state
- call hooks/actions
- no business-critical logic
- no direct state transitions

hooks:
- screen orchestration
- local UI state
- call api clients

api clients:
- typed backend calls
- no business rules

components:
- reusable UI only
- no API calls unless explicitly approved

theme:
- design tokens and Telegram theme mapping

## Prohibited

- DB queries in routes.py
- business rules inside React components
- permissions decided in UI
- state updates without backend state machine
- hardcoded fake production metrics
- giant functions
- duplicated logic between frontend and backend
- one function doing DB, audit, storage, notification and response

## Naming examples

Use explicit names:

- create_order_atomic()
- hold_ad_for_order()
- release_ad_after_cancel()
- confirm_payment_received()
- mark_order_delivered()
- report_payment()
- consume_credits_for_confirmed_payment()
- write_audit_event()
- enqueue_notification()
- create_stripe_checkout_session()
- handle_stripe_payment_succeeded()

## Change review before cut

Before any slice is marked READY_FOR_OWNER_REVIEW, builder must inspect exact changed lines and report:

- files changed
- line ranges changed
- functions changed
- contracts satisfied
- tests executed
- risk remaining
- files explicitly not touched
