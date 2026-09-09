# BUILDER_RULES.md

## Regla madre

No construir ninguna feature si no tiene:

- tabla/modelo afectado
- enum/estado oficial
- actor permitido
- permiso RBAC
- endpoint/API contract
- audit event si cambia estado/datos sensibles
- error esperado
- test minimo
- disclaimer/copy requerido si toca creditos, metodos publicados, verificacion o responsabilidad

## Arquitectura obligatoria

NODO debe construirse como software profesional, modular y mantenible.

Prohibido construir funciones Frankenstein. Ninguna funcion puede mezclar en un solo bloque:

- validacion
- permisos
- queries DB
- logica de negocio
- transiciones de estado
- auditoria
- storage
- notificaciones
- response HTTP

Cada cambio debe seguir 00_GOVERNANCE/CODE_ARCHITECTURE_MASTER.md.

## Proceso obligatorio por tarea

1. Leer SOURCE_OF_TRUTH.
2. Leer BUILDER_RULES.
3. Leer ENGINEERING_GUARDRAILS.
4. Leer CODE_ARCHITECTURE_MASTER.
5. Leer SPEC_MASTER.
6. Leer contracts del slice.
7. Leer screen specs afectados.
8. Implementar minimo necesario.
9. No ampliar scope.
10. Reportar archivos tocados.
11. Ejecutar QA definido.
12. Entregar BUILDER_REPORT.

## Regla antes de cortar

Antes de declarar un slice listo, el builder debe revisar las lineas exactas modificadas.

El reporte final debe incluir:

- archivos cambiados
- lineas cambiadas
- funciones modificadas
- contrato cumplido por cada cambio
- tests ejecutados
- riesgos residuales
- que NO se toco

No usar DONE, COMPLETE, READY o LISTO si no se revisaron lineas, QA, permisos, enums, disclaimers y BUILDER_REPORT.

## Auditorias obligatorias

Cada slice debe cumplir `00_GOVERNANCE/ENGINEERING_GUARDRAILS.md`.

Si alguna auditoria obligatoria encuentra un hallazgo `CRITICAL` o `HIGH`, el slice queda bloqueado aunque compile y aunque los tests puntuales pasen.

## Estados correctos

- READY_FOR_BUILDER: documentacion suficiente para construir el slice.
- READY_FOR_OWNER_REVIEW: tecnicamente revisado y probado.
- PILOT_CONTROLLED_REVIEW_REQUIRED: candidato listo para revision Owner de piloto pequeno con riesgos documentados.
- READY_FOR_REAL_USE: solo el owner lo autoriza.
- READY_FOR_PRODUCTION: solo el owner lo autoriza despues de legal, rollback, backup/restore, alertas, ambientes separados y evidencia completa.

El builder no puede declarar `READY_FOR_REAL_USE` ni `READY_FOR_PRODUCTION`.
