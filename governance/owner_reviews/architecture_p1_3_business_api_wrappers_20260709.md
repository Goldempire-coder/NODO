# architecture_p1_3_business_api_wrappers

## Estado

PASSED_AFTER_FIX

## Objetivo

Sacar rutas API directas de los hooks de la Mini App Negocio y moverlas a wrappers por dominio.

## Problema corregido

La Mini App Negocio ya estaba separada visualmente, pero sus hooks todavia tenian rutas `/api/v1/business/...`, `/api/v1/surface/session` y rutas de chat de orden pegadas adentro. Eso mezcla UI/estado con transporte API y hace mas dificil escalar o auditar seguridad por superficie.

## Correccion aplicada

Se agregaron o completaron wrappers:

- `apps/web/src/api/businesses.ts`
- `apps/web/src/api/surface.ts`
- `apps/web/src/api/businessAds.ts`
- `apps/web/src/api/businessOrders.ts`
- `apps/web/src/api/credits.ts`
- `apps/web/src/api/chat.ts` reutilizado para chat de orden

Se actualizaron hooks negocio:

- `apps/web/src/hooks/business-mini-app/useBusinessAccessModel.ts`
- `apps/web/src/hooks/business-mini-app/useBusinessAdsModel.ts`
- `apps/web/src/hooks/business-mini-app/useBusinessOrdersModel.ts`
- `apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts`
- `apps/web/src/hooks/business-mini-app/useBusinessChatModel.ts`

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
rg -n -F '"/api/v1/business' apps\web\src\hooks\business-mini-app apps\web\src\hooks\useBusinessMiniAppModel.ts
rg -n -F '"/api/v1/surface/session' apps\web\src\hooks\business-mini-app apps\web\src\hooks\useBusinessMiniAppModel.ts
rg -n -F '"/api/v1/orders/' apps\web\src\hooks\business-mini-app apps\web\src\hooks\useBusinessMiniAppModel.ts
```

Resultados:

```txt
NO_BUSINESS_ROUTE_LITERAL_MATCHES
NO_SURFACE_ROUTE_LITERAL_MATCHES
NO_ORDER_CHAT_ROUTE_LITERAL_MATCHES
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

Queda pendiente el corte equivalente para Admin Web. `useAdminWebModel.ts` sigue concentrando muchas rutas admin y responsabilidades en un solo hook grande.
