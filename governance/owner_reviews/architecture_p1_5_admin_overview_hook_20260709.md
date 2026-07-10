# architecture_p1_5_admin_overview_hook

## Estado

PASSED_AFTER_FIX

## Objetivo

Separar el primer dominio interno de `useAdminWebModel.ts` sin cambiar comportamiento: dashboard, metricas y jobs.

## Problema corregido

Aunque las rutas API admin ya estaban en wrappers, `useAdminWebModel.ts` seguia concentrando todo el estado y acciones del Admin Web. El primer bloque extraido fue el menos riesgoso: overview operacional.

## Correccion aplicada

Archivos creados:

- `apps/web/src/hooks/admin-web/helpers.ts`
- `apps/web/src/hooks/admin-web/useAdminOverviewModel.ts`

Archivo actualizado:

- `apps/web/src/hooks/useAdminWebModel.ts`

Responsabilidad movida al nuevo hook:

- `dashboard`
- `metrics`
- `jobRuns`
- `loadDashboard`
- `loadMetrics`
- `loadJobs`
- `dryRunJobs`

`useAdminWebModel.ts` conserva la composicion principal y reexporta `AdminWebJobRun` para no romper las pantallas existentes.

## Evidencia

Lineas:

```txt
useAdminWebModel.ts: 572 lineas
useAdminOverviewModel.ts: 107 lineas
```

Scan:

```txt
rg -n "getAdminDashboard|getAdminMetrics|listAdminJobRuns|dryRunExpireAndEscalateOrders|const \[dashboard|const \[metrics|const \[jobRuns|const loadDashboard|const loadMetrics|const loadJobs|const dryRunJobs" apps\web\src\hooks\useAdminWebModel.ts
```

Resultado:

```txt
NO_OVERVIEW_LOGIC_IN_MAIN_MODEL
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
- No se cambiaron reglas admin.
- No se cambio UI visual.
- No se toco backend de producto.
- No se hizo deploy.
- No se declaro `READY_FOR_REAL_USE`.

## Riesgo residual

Quedan pendientes nuevos cortes pequenos del Admin Web:

- businesses/intake
- orders/disputes
- credits
- audit
