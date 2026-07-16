# slice_35_business_mini_app_afos_hardening - Owner Audit

Estado: OWNER_REVIEW_FIXES_VALIDATED

Fecha: 2026-07-16

Auditor: Codex

## Veredicto

El slice mejora seguridad, fluidez y separacion de responsabilidades de la Mini App Negocio. La auditoria encontro dos brechas MEDIUM y ambas quedaron corregidas en esta pasada:

1. Zelle ahora exige `Idempotency-Key` en backend para crear, editar y borrar.
2. `OBSERVABILITY_CONTRACT.md` quedo alineado con el breadcrumb real `business_order_reject_payment_report`.

No encontre hallazgos CRITICAL ni HIGH confirmados en esta auditoria.

## Hallazgos

### MEDIUM - Zelle declara idempotencia, pero el backend no la exige

Evidencia:

- `control_plane/09_SLICES/slice_35_business_mini_app_afos_hardening/SENSITIVE_ACTION_MATRIX.md` marca agregar, editar y borrar Zelle con `Idempotency-Key = Si`.
- La auditoria original detecto que payment methods aceptaban omitir ese header y que el cliente de create Zelle generaba la clave en el wrapper de API.

Impacto:

Un cliente manipulado podria omitir el header. La operacion sigue protegida por PIN, ownership y validaciones, por eso no es HIGH, pero contradice la matriz AFOS y deja la idempotencia como best effort.

Fix aplicado:

- `apps/api/app/modules/businesses/service.py` llama `require_idempotency_key` en `create_own_payment_method`, `update_own_payment_method` y `delete_own_payment_method`.
- `apps/web/src/api/businesses.ts` ya recibe la clave desde el hook; no la inventa con `Date.now()`.
- `apps/web/src/hooks/business-mini-app/useBusinessAccessModel.ts` pasa `idempotencyKey("business_payment_method_create")` al crear Zelle.
- `apps/api/tests/test_business_access_control.py` cubre missing idempotency para `POST`, `PATCH` y `DELETE` de payment methods.

Estado: FIXED_AND_VALIDATED.

### MEDIUM - Drift de nombre de breadcrumb de rechazo de reporte

Evidencia:

- La auditoria original encontro un nombre de breadcrumb distinto entre `OBSERVABILITY_CONTRACT.md`, la matriz sensible y `useBusinessOrdersModel.ts`.

Impacto:

No rompe runtime, pero si rompe gobernanza: un validator futuro puede buscar el evento incorrecto.

Fix aplicado:

- `control_plane/09_SLICES/slice_35_business_mini_app_afos_hardening/OBSERVABILITY_CONTRACT.md` ahora lista `business_order_reject_payment_report`.
- `apps/api/tests/test_auth_lifecycle_static.py` valida el nombre real.

Estado: FIXED_AND_VALIDATED.

## Controles verificados como OK

- `business_availability_update` ahora exige PIN desbloqueado e `Idempotency-Key`.
- `business_availability_update` usa backend authority, audit event e idempotency store.
- Frontend conserva accion pendiente de online/offline y la reintenta tras PIN.
- Base USDC doc drift quedo alineado con `/tx-hash` y `pending_payment`.
- Botones sensibles ya usan estados por accion: credit tx, generar pago, ordenes, chat, soporte y Zelle.
- Breadcrumbs nuevos no incluyen wallet completa, Zelle completo, PIN ni tx hash completo.
- Anuncios estan mejor separados en componentes `ads/BusinessAdCard`, `ads/BusinessAdDetailPanel` y helpers.

## Validaciones reproducidas

```powershell
python -m pytest apps/api/tests/test_business_access_control.py apps/api/tests/test_auth_lifecycle_static.py -q --tb=short
```

Resultado: `16 passed, 1 warning`.

```powershell
python -m pytest apps/api/tests -q
```

Resultado: `357 passed, 1 warning`.

```powershell
python -m ruff check apps/api scripts
```

Resultado: `All checks passed!`.

```powershell
python -m compileall apps/api apps/web/src scripts
```

Resultado: passed.

```powershell
pnpm --filter @nodo/web build
```

Resultado inicial: blocked, `node` no estaba en PATH.

```powershell
$env:PATH="C:\Users\carlo\AppData\Local\Programs\cursor\resources\app\resources\helpers;$env:PATH"; pnpm --filter @nodo/web build
```

Resultado: passed.

```powershell
git diff --check
```

Resultado: exit 0, solo warnings CRLF existentes.

## Estado final

OWNER_REVIEW_FIXES_VALIDATED

Las brechas encontradas por la auditoria fueron corregidas y validadas. Sigue sin ser autorizacion de deploy ni `READY_FOR_REAL_USE`; solo cierra la revision tecnica del slice en repo.
