# Owner Verification Protocol

Este protocolo se ejecuta despues de que Builder declara un slice como `READY_FOR_OWNER_REVIEW`.

## Regla madre

Un slice no queda aceptado solo porque Builder lo reporte como listo. Debe pasar una verificacion independiente de Codex/Owner contra contratos, codigo, pruebas y evidencia.

## Entradas obligatorias

Builder debe entregar:

- `governance/builder_reports/<slice>_BUILDER_REPORT.md`
- evidencia en `evidence/slice_runs/`
- resultados de tests cuando aplique
- lista de archivos y lineas modificadas
- dependencias instaladas con version y motivo
- riesgos residuales
- lista de lo que NO toco

Si falta cualquiera de estas entradas, el slice queda:

```txt
BLOCKED_BY_MISSING_EVIDENCE
```

## Verificacion independiente

Codex/Owner debe revisar:

- scope real contra contrato del slice
- archivos modificados contra limites del slice
- endpoints contra API contracts
- tablas/migraciones contra data contracts
- roles/RBAC contra matriz de permisos
- errores contra `ERROR_CONTRACT.md`
- seguridad contra contratos de `05_SECURITY`
- UI contra `07_UI_UX` y pantallas `08_SCREENS`
- tests declarados contra tests realmente ejecutados
- evidencia generada
- riesgos residuales

## Pruebas minimas a repetir

Siempre que aplique, Codex/Owner debe re-ejecutar:

- build frontend
- tests backend
- runner del slice
- lint/typecheck/compile
- busquedas de terminos prohibidos
- revision de migraciones
- revision de secretos en frontend/logs

## Resultado de verificacion

Estados validos:

```txt
OWNER_ACCEPTED_FOR_NEXT_SLICE
OWNER_REJECTED_REQUIRES_FIXES
BLOCKED_BY_MISSING_EVIDENCE
BLOCKED_BY_CONTRACT_CONFLICT
BLOCKED_BY_SECURITY_GAP
BLOCKED_BY_SCOPE_EXPANSION
```

## Reparacion

Si la verificacion encuentra errores corregibles dentro del mismo slice, se puede autorizar fix del mismo slice.

Si el error implica contrato incompleto o contradiccion documental, primero se corrige documentacion y luego Builder reintenta.

Si el error implica arquitectura incorrecta, scope creep, seguridad rota o datos incompatibles, el slice puede requerir reconstruccion parcial o completa.

## Prohibido

- Aceptar un slice sin evidencia.
- Aceptar un slice con tests no ejecutados sin razon.
- Aceptar un slice que rompe contratos de slices futuros.
- Declarar `READY_FOR_REAL_USE`.

