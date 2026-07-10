# architecture_p1_1_surface_view_types

## Estado

PASSED_AFTER_FIX

## Objetivo

Separar los tipos de vista por superficie para evitar que Cliente, Mini App Negocio y Admin Web compartan un tipo global mezclado.

## Problema corregido

El frontend todavia arrastraba el concepto global `BusinessView`, que venia del workspace viejo y mezclaba superficies. Eso dejaba una frontera debil: una pantalla o hook podia aceptar vistas de otra superficie aunque ya existan apps separadas.

## Correccion aplicada

- Cliente usa `ClientView`.
- Mini App Negocio usa `BusinessMiniAppView`.
- Admin Web conserva su tipo propio de vista dentro de su modelo.
- Se elimino el nombre `BusinessView` de `apps/web/src`.
- Se renombro el fallback viejo de negocio para que ya no conserve el nombre ambiguo.

## Archivos revisados/ajustados

- `apps/web/src/constants/clientViews.ts`
- `apps/web/src/constants/businessViews.ts`
- `apps/web/src/types/domain.ts`
- `apps/web/src/types/ui.ts`
- `apps/web/src/hooks/useClientWorkspaceModel.ts`
- `apps/web/src/hooks/workspace/useClientWorkspaceState.ts`
- `apps/web/src/screens/client/RemitterScreens.tsx`
- `apps/web/src/hooks/useBusinessMiniAppModel.ts`
- `apps/web/src/hooks/business-mini-app/helpers.ts`
- `apps/web/src/hooks/business-mini-app/useBusinessAdsModel.ts`
- `apps/web/src/hooks/business-mini-app/useBusinessOrdersModel.ts`
- `apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts`
- `apps/web/src/hooks/business-mini-app/useBusinessChatModel.ts`
- `apps/web/src/hooks/business-mini-app/useBusinessTelegramControls.ts`
- `apps/web/src/screens/business-app/BusinessMiniAppShell.tsx`

## Evidencia

Comandos ejecutados:

```txt
rg -n "BusinessView" apps\web\src
```

Resultado:

```txt
NO_MATCHES
```

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
- No se cambiaron reglas de negocio.
- No se cambiaron pantallas visualmente.
- No se toco backend de producto.
- No se hizo deploy.
- No se declaro `READY_FOR_REAL_USE`.

## Riesgo residual

Quedan pendientes otros cortes de arquitectura ya identificados: separar API wrappers/hook models por dominio y revisar superficies con pruebas visuales reales. Este corte solo cerro el tipo global mezclado.
