# architecture_p1_4_admin_api_wrappers

## Estado

PASSED_AFTER_FIX

## Objetivo

Sacar rutas API directas de `useAdminWebModel.ts` y moverlas a wrappers de Admin Web.

## Problema corregido

`useAdminWebModel.ts` concentraba estado, acciones, filtros y construccion directa de rutas `/api/v1/admin/...`. Eso hacia mas dificil auditar permisos, headers, idempotencia y cambios de endpoints del panel admin.

## Correccion aplicada

Se completo:

- `apps/web/src/api/admin.ts`

Con wrappers para:

- dashboard
- metrics
- businesses
- business review
- private document view-url
- orders
- disputes
- dispute resolution
- audit logs
- credit purchases
- credit adjustments
- job runs
- business intake list/detail/delete/accept
- expire/escalate dry-run

Se actualizo:

- `apps/web/src/hooks/useAdminWebModel.ts`

El hook mantiene estado y decisiones UI, pero ya no construye rutas admin directas.

## Evidencia

Comandos ejecutados:

```txt
corepack pnpm --filter @nodo/web build
```

Resultado:

```txt
PASS
```

```txt
$env:PYTHONPATH='apps/api'; python -m pytest apps\api\tests -q
```

Resultado:

```txt
133 passed, 1 warning
```

```txt
python -m ruff check apps\api scripts
```

Resultado:

```txt
All checks passed
```

```txt
python -m compileall apps\api scripts
```

Resultado:

```txt
PASS
```

Scans:

```txt
rg -n -F '"/api/v1/admin' apps\web\src\hooks\useAdminWebModel.ts
rg -n "new URLSearchParams|request<" apps\web\src\hooks\useAdminWebModel.ts
```

Resultados:

```txt
NO_ADMIN_ROUTE_LITERAL_MATCHES
NO_ADMIN_INLINE_ROUTE_BUILDERS
```

## Alcance no tocado

- No se cambiaron endpoints.
- No se cambiaron payloads.
- No se cambiaron reglas de admin.
- No se cambio UI visual.
- No se toco backend de producto.
- No se hizo deploy.
- No se declaro `READY_FOR_REAL_USE`.

## Riesgo residual

`useAdminWebModel.ts` sigue siendo grande y mezcla varios dominios de estado admin. El siguiente corte recomendado es dividirlo en hooks pequenos por dominio:

- dashboard/metrics
- businesses/intake
- orders/disputes
- credits
- audit/jobs
