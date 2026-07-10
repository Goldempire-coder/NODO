# slice_14B1_business_access_control_contracts evidence

## Estado

READY_FOR_OWNER_REVIEW

## Evidencia funcional

- `GET /api/v1/surface/session` implementado bajo `/api/v1`.
- Header `X-NODO-Surface: business_mini_app` requerido para el gate de negocio.
- `business_access_links` implementado como modelo canonico de acceso.
- Mini App Negocio llama `surface/session` antes de hidratar el espacio operativo.
- `/businesses/me` no aparece en `apps/web/src/hooks/useBusinessMiniAppModel.ts`.
- Operaciones sensibles de negocio validan acceso activo mediante policy comun.

## Evidencia de seguridad

- Usuario bloqueado en `surface/session`: `USER_BLOCKED`.
- Usuario no activo en policy de superficie: `USER_NOT_ACTIVE`.
- Link suspendido: `BUSINESS_ACCESS_SUSPENDED`.
- Link revocado: `BUSINESS_ACCESS_REVOKED`.
- Link bloqueado: `BUSINESS_ACCESS_BLOCKED`.
- Negocio suspendido: `BUSINESS_SUSPENDED`.
- Negocio bloqueado: `BUSINESS_BLOCKED`.
- Negocio no aprobado: `BUSINESS_NOT_APPROVED`.
- Admin mutations requieren `Idempotency-Key` y `reason`.
- `support` queda bloqueado para mutaciones de access links.
- Audit events cubiertos en tests: `business_access_linked`, `business_access_suspended`, `business_access_reactivated`, `business_access_unlinked`, `business_access_blocked`, `surface_access_denied`.

## Validaciones ejecutadas

```txt
corepack pnpm --filter @nodo/web build
PASS
```

```txt
$env:PYTHONPATH='apps/api;C:\Users\carlo\AppData\Roaming\Python\Python314\site-packages'; python -m pytest apps\api\tests\test_business_access_control.py apps\api\tests\test_ads_marketplace.py -q --tb=short
18 passed, 1 warning in 2.86s
```

```txt
$env:PYTHONPATH='apps/api;C:\Users\carlo\AppData\Roaming\Python\Python314\site-packages'; python -m pytest apps\api\tests -q --tb=short
110 passed, 1 warning in 15.77s
```

```txt
python -m ruff check apps\api scripts
All checks passed!
```

```txt
python -m compileall apps scripts
PASS
```

## Scans

```txt
rg -n "surface/session|X-NODO-Surface" apps\web\src\hooks\useBusinessMiniAppModel.ts
177:      const session = await request("/api/v1/surface/session", {
178:        headers: { "X-NODO-Surface": "business_mini_app" }
```

```txt
rg -n "/api/v1/businesses/me|/businesses/me" apps\web\src\hooks\useBusinessMiniAppModel.ts
NO MATCH
```

```txt
rg -n "ClientWorkspace|AdminWebWorkspace|RemitterScreens|VerificationScreens|BusinessOperationsScreens|AdminConsoleScreens" apps\web\src\screens\business-app apps\web\src\hooks\useBusinessMiniAppModel.ts
NO MATCH
```

```txt
rg -n "storage_path|account_value|SUPABASE_SERVICE_ROLE_KEY|BOT_TOKEN|JWT_SECRET|escrow|fondos protegidos|pago garantizado|garant[ií]a de entrega|NODO recibió dinero" apps\web\src\screens\business-app apps\web\src\hooks\useBusinessMiniAppModel.ts apps\web\out
NO MATCH
```

## Riesgos residuales

- Aplicacion real de migracion pendiente de autorizacion de entorno.
- Endpoints legacy de negocio siguen existiendo, pero no son gate de Mini App Negocio.
- `operator` reservado para futuro; acceso operativo actual se mantiene en `business_owner`.

