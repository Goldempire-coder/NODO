# Cut Review Protocol

Antes de cerrar un slice, Builder debe revisar exactamente lo que corto o modifico.

## Reporte obligatorio

Cada slice construido debe entregar reporte final en:

```txt
governance/builder_reports/<slice>_BUILDER_REPORT.md
```

Debe usar como base:

```txt
governance/builder_reports/BUILDER_REPORT_REQUIRED_TEMPLATE.md
```

## Revision requerida

El reporte final debe incluir:

- archivos cambiados
- lineas cambiadas
- funciones o componentes modificados
- contrato que justifica cada cambio
- dependencias instaladas o modificadas con version y motivo
- pruebas ejecutadas
- pruebas no ejecutadas y razon
- evidencia creada
- riesgos residuales
- archivos que no se tocaron

## Verificacion posterior

Despues del reporte de Builder, Codex/Owner debe ejecutar:

```txt
governance/workflow/OWNER_VERIFICATION_PROTOCOL.md
```

Builder no puede saltar esta verificacion.

## Prohibido

- Marcar listo sin revisar lineas.
- Reportar "todo bien" sin evidencia.
- Mezclar cambios de otro slice.
- Declarar `READY_FOR_REAL_USE`.

## Estados de salida

Permitidos:

```txt
READY_FOR_OWNER_REVIEW
BLOCKED_BY_MISSING_CONTRACT
BLOCKED_BY_CONTRACT_CONFLICT
BLOCKED_BY_SECURITY_GAP
BLOCKED_BY_UI_CONTRACT_GAP
BLOCKED_BY_SCOPE_EXPANSION
```

No permitido para Builder:

```txt
READY_FOR_REAL_USE
```
