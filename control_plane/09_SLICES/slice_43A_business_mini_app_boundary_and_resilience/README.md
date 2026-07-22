# slice_43A_business_mini_app_boundary_and_resilience

Estado contractual: `READY_FOR_OWNER_APPROVAL_TO_BUILD_43A`

## Objetivo

Cerrar el primer paquete de riesgos detectados en la auditoria red-team de la
Mini App Negocio sin mezclar una limpieza grande de UI, paginacion o auth.

Este slice protege los limites entre datos internos y datos visibles para el
negocio, y evita que la app muestre estados falsos cuando hay fallos temporales
de red o de refresh.

## Por que existe

La inspeccion encontro que la sesion de negocio devuelve `risk_level`, una
senal interna que debe quedarse en Admin. Tambien encontro fallos de resiliencia
visual: saldo/contadores pueden desaparecer ante errores temporales y la
telemetria de transicion puede medir el tiempo equivocado.

## Resultado permitido

- `READY_FOR_OWNER_REVIEW`
- `BLOCKED_BY_EXPLICIT_EVIDENCE`

## Resultado no permitido

- `READY_FOR_REAL_USE`
- `APPROVED_FOR_PRODUCTION`
- `PRODUCTION_READY`

## Documentos del slice

- `SCOPE.md`
- `SECURITY_CONTRACT.md`
- `UI_RESILIENCE_CONTRACT.md`
- `OBSERVABILITY_CONTRACT.md`
- `QA.md`
- `DO_NOT_BUILD.md`
- `BUILDER_PROMPT.md`
