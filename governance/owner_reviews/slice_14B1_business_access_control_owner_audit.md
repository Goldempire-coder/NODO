# OWNER AUDIT - slice_14B1_business_access_control_contracts

## Estado final

PASSED_AFTER_OWNER_AUDIT_FIX

## Resultado

Auditoria profunda ejecutada sobre el build entregado por builder para `slice_14B1_business_access_control_contracts`.

No se hizo deploy. No se declaro `READY_FOR_REAL_USE`.

## Hallazgos corregidos

### 1. Constraint de owner activo incompleto

El contrato exige:

- `linked_by_admin_id` not null.
- Un solo link `active` por `(business_id, user_id, role_in_business)`.
- Un solo `owner` activo por negocio.

La migracion inicial solo garantizaba un link activo por `(business_id, user_id)` y dejaba `linked_by_admin_id` nullable.

Correccion aplicada:

- `database/migrations/0013_slice_14B1_business_access_links.up.sql`
  - `linked_by_admin_id uuid not null`.
  - unique parcial `business_access_links_active_business_user_idx` ahora usa `(business_id, user_id, role_in_business)` where `status = 'active'`.
  - unique parcial `business_access_links_active_owner_idx` para un solo owner activo por negocio.
- `database/migrations/0013_slice_14B1_business_access_links.down.sql`
  - rollback elimina el indice nuevo.

### 2. Link admin podia apuntar a usuario que no era owner real

El endpoint admin podia crear un link `owner` para un usuario distinto a `businesses.owner_user_id`. Luego `surface/session` lo negaba por ownership, dejando un link activo inutil.

Correccion aplicada:

- `apps/api/app/modules/businesses/service.py`
  - Para MVP, `role_in_business = owner` exige que `payload.user_id == business.owner_user_id`.
  - Transferencia de owner queda fuera hasta contrato futuro.

### 3. Repo no bloqueaba segundo owner activo

Aunque la DB ahora tiene unique parcial, el repo in-memory/Postgres tambien debe fallar con error seguro.

Correccion aplicada:

- `apps/api/app/modules/businesses/repository.py`
  - `create_access_link` rechaza segundo owner activo con `CONFLICT`.

### 4. Negocio bloqueado podia perder razon correcta

`get_active_business_for_owner` filtraba `verification_status <> blocked`. Eso podia convertir un negocio bloqueado en falso "no business/link" en el gate.

Correccion aplicada:

- `apps/api/app/modules/businesses/repository.py`
  - El gate ahora puede recuperar el negocio del owner y devolver `BUSINESS_BLOCKED`/`BUSINESS_SUSPENDED` segun corresponda.

### 5. `surface/session` exponia `telegram_id`

La postura previa de auth evita exponer `telegram_id` como identificador publico.

Correccion aplicada:

- `apps/api/app/modules/businesses/access_control.py`
  - `public_user_for_surface` ya no incluye `telegram_id`.

## Pruebas agregadas

Archivo:

- `apps/api/tests/test_business_access_control.py`

Casos agregados:

- `surface/session` permitido no expone `telegram_id`.
- Negocio bloqueado devuelve `BUSINESS_BLOCKED`.
- Admin no puede crear link owner para un usuario distinto al owner real del negocio.

## Verificacion ejecutada

- Focus pytest:
  - `$env:PYTHONPATH='apps/api'; python -m pytest apps/api/tests/test_business_access_control.py -q`
  - Resultado: `5 passed, 1 warning`

- Pytest acumulado:
  - `$env:PYTHONPATH='apps/api'; python -m pytest apps/api/tests -q`
  - Resultado: `110 passed, 1 warning`

- Ruff:
  - `python -m ruff check apps/api scripts`
  - Resultado: OK

- Compileall:
  - `python -m compileall apps scripts`
  - Resultado: OK

- Frontend build:
  - `corepack pnpm --filter @nodo/web build`
  - Resultado: OK

- Scan migracion:
  - `business_access_links_active_owner_idx` presente.
  - `linked_by_admin_id uuid not null` presente.

- Scan Mini App Negocio:
  - `apps/web/src/hooks/useBusinessMiniAppModel.ts` usa `/api/v1/surface/session`.
  - Header `X-NODO-Surface: business_mini_app` presente.
  - No se encontro `/api/v1/businesses/me` como gate en source de business-app.

- Scan secretos/datos privados en source web:
  - Sin hits para `storage_path`, `account_value`, `SUPABASE_SERVICE_ROLE_KEY`, `JWT_SECRET`, `BOT_TOKEN`.

## Riesgos residuales

- No se ejecuto migracion 0013 contra PostgreSQL/Supabase real en este turno.
- No se hizo smoke real de Mini App Negocio en Telegram tras el fix.
- Warning Starlette/httpx heredado sigue presente.

## Veredicto

`slice_14B1_business_access_control_contracts` queda aprobado tecnicamente despues de correcciones de auditoria owner.

No es `READY_FOR_REAL_USE`.
