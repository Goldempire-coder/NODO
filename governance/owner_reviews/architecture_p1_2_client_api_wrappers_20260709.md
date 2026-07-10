# architecture_p1_2_client_api_wrappers

## Estado

PASSED_AFTER_FIX

## Objetivo

Sacar rutas API directas de los hooks de la Mini App Cliente y moverlas a wrappers por dominio.

## Problema corregido

Los archivos `apps/web/src/api/*.ts` existian, pero varios eran placeholders que solo reexportaban `apiRequest`. Eso hacia que hooks de cliente siguieran con rutas `/api/v1/...` pegadas adentro. Ese patron vuelve dificil escalar porque UI, estado y transporte API quedan mezclados.

## Correccion aplicada

Se agregaron wrappers reales para dominio cliente:

- `apps/web/src/api/ads.ts`
- `apps/web/src/api/orders.ts`
- `apps/web/src/api/chat.ts`
- `apps/web/src/api/paymentReports.ts`
- `apps/web/src/api/users.ts`
- `apps/web/src/api/client.ts`

Se actualizaron hooks cliente para usar esos wrappers:

- `apps/web/src/hooks/useClientWorkspaceModel.ts`
- `apps/web/src/hooks/workspace/useClientMarketplaceModel.ts`
- `apps/web/src/hooks/workspace/useRemitterOrdersModel.ts`
- `apps/web/src/hooks/workspace/usePaymentReportModel.ts`
- `apps/web/src/hooks/workspace/useClientChatDisputesModel.ts`

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

```txt
rg -n "request\(`?/api/v1/(ads|orders|users/me)" apps\web\src\hooks\workspace apps\web\src\hooks\useClientWorkspaceModel.ts
```

Resultado:

```txt
NO_CLIENT_DIRECT_ROUTE_MATCHES
```

## Alcance no tocado

- No se cambiaron endpoints.
- No se cambiaron payloads.
- No se cambiaron reglas de negocio.
- No se cambio UI visual.
- No se toco backend de producto.
- No se hizo deploy.
- No se declaro `READY_FOR_REAL_USE`.

## Riesgo residual

Este corte solo cubre la Mini App Cliente. Todavia quedan pendientes:

- wrappers API de Mini App Negocio
- wrappers API de Admin Web
- separar el modelo admin grande en dominios mas pequenos
- pruebas visuales/manuales por superficie
