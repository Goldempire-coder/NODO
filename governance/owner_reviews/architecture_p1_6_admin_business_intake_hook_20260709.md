# architecture_p1_6_admin_business_intake_hook

## Estado

PASSED_AFTER_FIX

## Objetivo

Separar del Admin Web el dominio de negocios e intake sin cambiar comportamiento.

## Problema corregido

`useAdminWebModel.ts` todavia mezclaba revision de negocios, apertura de documentos privados, solicitudes de intake, borrado de intake y creacion de negocio desde intake. Ese bloque tiene riesgo funcional porque conecta captacion, aprobacion y acceso operativo.

## Correccion aplicada

Archivo creado:

- `apps/web/src/hooks/admin-web/useAdminBusinessIntakeModel.ts`

Responsabilidad movida:

- `businesses`
- `selectedBusiness`
- `businessIntakes`
- `selectedBusinessIntake`
- `businessFilter`
- `intakeFilter`
- `intakePublicBusinessName`
- `loadBusinesses`
- `loadPendingBusinesses`
- `openBusiness`
- `reviewBusiness`
- `openDocument`
- `loadBusinessIntakes`
- `openBusinessIntake`
- `deleteBusinessIntake`
- `createBusinessFromIntake`

`useAdminWebModel.ts` queda como composer y reexporta tipos para no romper pantallas existentes.

## Evidencia

Lineas:

```txt
useAdminWebModel.ts: 369 lineas
useAdminBusinessIntakeModel.ts: 268 lineas
```

Scan:

```txt
rg -n "acceptAdminBusinessIntake|deleteAdminBusinessIntake|getAdminBusiness|getAdminBusinessDocumentViewUrl|getAdminBusinessIntake|listAdminBusinesses|listAdminBusinessIntakes|listPendingAdminBusinesses|reviewAdminBusiness|const \[businesses|const \[selectedBusiness|const \[businessIntakes|const \[selectedBusinessIntake|const \[businessFilter|const \[intakeFilter|const \[intakePublicBusinessName|const loadBusinesses|const loadPendingBusinesses|const openBusiness|const reviewBusiness|const openDocument|const loadBusinessIntakes|const openBusinessIntake|const deleteBusinessIntake|const createBusinessFromIntake" apps\web\src\hooks\useAdminWebModel.ts
```

Resultado:

```txt
NO_BUSINESS_INTAKE_LOGIC_IN_MAIN_MODEL
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
- No se cambiaron reglas de negocio/intake.
- No se cambio UI visual.
- No se toco backend de producto.
- No se hizo deploy.
- No se declaro `READY_FOR_REAL_USE`.

## Riesgo residual

Quedan pendientes nuevos cortes pequenos del Admin Web:

- orders/disputes
- credits
- audit
