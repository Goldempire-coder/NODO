# SLICE_25A_CACHE_CONSISTENCY_HARDENING_OWNER_AUDIT

Fecha: 2026-07-11
Estado: PASSED_OWNER_AUDIT_WITH_LIMITS
Decision: CACHE STRATEGY READY WITH LIMITS

## Alcance auditado

Se reviso el resultado del builder para `slice_25A_cache_consistency_hardening`.

Areas revisadas:

- Fallback de marketplace cuando shared cache/Redis falla.
- Invalidacion de `auth_user_cache` tras cambios admin de status.
- Cache key por rol para dashboard/metrics admin.
- Logs ligeros `cache_unavailable` y `cache_invalidation`.
- Tests de marketplace/admin cache.

No se agrego cache nueva para dinero, ledger, ordenes, tickets, staff permissions, access links, signed URLs ni storage privado.

## Resultado de auditoria

El build del builder es valido. Se agrego un ajuste adicional durante owner audit:

- `RedisTTLCache.get_json` ahora trata JSON corrupto en Redis como `CacheUnavailableError`.
- Esto evita que un valor corrupto en cache tumbe marketplace reads; el sistema debe degradar a miss/DB.

Archivos ajustados durante owner audit:

- `apps/api/app/shared/cache.py`
- `apps/api/tests/test_ads_marketplace.py`

## Validaciones ejecutadas

```text
python -m pytest apps\api\tests\test_ads_marketplace.py apps\api\tests\test_admin_users_business_control.py -q --tb=short
29 passed, 1 warning

python -m pytest apps\api\tests -q --tb=short
226 passed, 1 warning

python -m ruff check apps\api scripts
All checks passed!

python -m compileall apps\api apps\web\src scripts
OK

corepack pnpm --filter @nodo/web build
OK
```

Scan frontend:

```text
FRONTEND_SENSITIVE_SCAN_CLEAN
```

## Confirmaciones

- No se agrego cache nueva.
- No se cacheo dinero, ledger, ordenes, soporte, staff permissions, access links ni signed URLs.
- No se agregaron migraciones.
- No se hizo deploy.
- No se declaro `READY_FOR_REAL_USE`.

## Riesgos residuales

- Marketplace read auth claim TTL sigue siendo una ventana configurable para reads public-safe.
- Si Redis falla justo durante invalidacion, otros workers pueden conservar L1 local hasta TTL corto.
- No hay dashboards permanentes de hit ratio/cache latency en este slice.
- Falta staging real multi-worker con Upstash/Supabase/Railway.

## Veredicto

CACHE STRATEGY READY WITH LIMITS.
