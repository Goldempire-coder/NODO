# architecture_p1_7_admin_orders_disputes_hook

## Estado

PASSED_AFTER_FIX

## Objetivo

Separar del Admin Web el dominio de ordenes y disputas sin cambiar comportamiento.

## Problema corregido

`useAdminWebModel.ts` todavia mezclaba observacion de ordenes con resolucion admin de disputas. Ese bloque debe estar aislado porque disputa es una accion sensible con reason, RBAC, audit e idempotencia.

## Correccion aplicada

Archivo creado:

- `apps/web/src/hooks/admin-web/useAdminOrdersDisputesModel.ts`

Responsabilidad movida:

- `orders`
- `selectedOrder`
- `disputes`
- `selectedDispute`
- `orderFilter`
- `disputeFilter`
- `resolutionType`
- `loadOrders`
- `openOrder`
- `loadDisputes`
- `openDispute`
- `resolveDispute`

`useAdminWebModel.ts` queda como composer y reexporta tipos de detalle para no romper contratos internos.

## Evidencia

Lineas:

```txt
useAdminWebModel.ts: 289 lineas
useAdminOrdersDisputesModel.ts: 134 lineas
```

Scan:

```txt
rg -n "getAdminDispute|getAdminOrder|listAdminDisputes|listAdminOrders|resolveAdminDispute|const \[orders|const \[selectedOrder|const \[disputes|const \[selectedDispute|const \[orderFilter|const \[disputeFilter|const \[resolutionType|const loadOrders|const openOrder|const loadDisputes|const openDispute|const resolveDispute" apps\web\src\hooks\useAdminWebModel.ts
```

Resultado:

```txt
NO_ORDERS_DISPUTES_LOGIC_IN_MAIN_MODEL
```

Validacion:

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

## Alcance no tocado

- No se cambiaron endpoints.
- No se cambiaron payloads.
- No se cambiaron reglas de ordenes/disputas.
- No se cambio UI visual.
- No se toco backend de producto.
- No se hizo deploy.
- No se declaro `READY_FOR_REAL_USE`.

## Riesgo residual

Quedan pendientes nuevos cortes pequenos del Admin Web:

- credits
- audit
