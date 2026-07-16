# BUILDER_PROMPT.md

Actua como Principal Software Architect, Application Security Reviewer y Frontend Reliability Engineer.

Proyecto: NODO
Slice: `slice_35_business_mini_app_afos_hardening`

## Objetivo

Endurecer la Mini App Negocio usando el checklist AFOS aplicado al flujo de negocio. No optimices al azar. No hagas deploy. No toques produccion. No cambies reglas financieras sin evidencia.

## Que vas a construir

1. Una matriz AFOS especifica de Mini App Negocio.
2. Una matriz de acciones sensibles.
3. Refactor minimo para separar responsabilidades donde el codigo aun este concentrado.
4. Instrumentacion segura para duracion de pantallas/acciones si falta.
5. Tests que protejan arquitectura, seguridad, ownership, idempotencia y UX operativa.
6. Reporte builder con evidencia reproducible.

## Que NO vas a tocar

- app cliente;
- admin redesign;
- produccion;
- deploy;
- infraestructura;
- wallets privadas;
- seed phrases;
- cambios de provider;
- reglas financieras nuevas;
- acreditacion sin verifier backend;
- microservicios, colas o Redis nuevo;
- c100+ product-gate.

## Orden obligatorio

1. Leer:
   - `governance/owner_reviews/business_mini_app_afos_audit_2026_07_16.md`
   - todos los documentos de este slice.
2. Inspeccionar archivos actuales de Mini App Negocio.
3. Entregar mini plan antes de editar:
   - hallazgo;
   - evidencia;
   - archivo;
   - cambio minimo;
   - prueba;
   - rollback.
4. Implementar cambios pequenos.
5. Ejecutar QA.
6. Entregar reporte.

## Validaciones obligatorias

Ejecuta los comandos de `QA.md`.

## Reporte final requerido

Entrega exactamente:

1. Estado final.
2. Hallazgos corregidos.
3. Hallazgos no corregidos.
4. Matriz AFOS creada.
5. Matriz de acciones sensibles creada.
6. Cambios realizados por archivo.
7. Pruebas ejecutadas con comandos y resultados.
8. Scans de secretos y resultados.
9. Riesgos pendientes por severidad.
10. Confirmaciones:
    - no deploy;
    - no produccion;
    - no wallet privada;
    - no secretos;
    - no reglas financieras nuevas;
    - no `READY_FOR_REAL_USE`.

Estado final permitido:

- `READY_FOR_OWNER_REVIEW`
- `BLOCKED_BY_EXPLICIT_EVIDENCE`
