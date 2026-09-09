# PROJECT_STATUS.md

Estado documental: STAGING_PILOT_PREPARATION.

Estado de producto: BUILT_IN_STAGING_PILOT_PREPARATION.

Fecha de corte documental: 2026-09-09.

## Significado del estado

STAGING_PILOT_PREPARATION significa que existe implementacion en `apps/api`, `apps/web`, migraciones, contratos y operaciones, pero el arbol documental gobierna todavia que se puede probar, desplegar y declarar.

No significa produccion abierta. El piloto controlado requiere evidencia actual, aceptacion Owner de riesgos residuales y alcance limitado.

## Estados permitidos

- PRE-BUILD: no hay software final; solo documentos y contratos.
- READY_FOR_BUILDER: un slice tiene contrato suficiente para construirse.
- IN_BUILD: el builder esta implementando un slice aprobado.
- READY_FOR_OWNER_REVIEW: el slice fue construido y probado tecnicamente.
- PILOT_CONTROLLED_REVIEW_REQUIRED: el candidato puede revisarse para piloto pequeno, con limites, evidencia y riesgos documentados.
- READY_FOR_REAL_USE: solo el owner lo autoriza despues de deploy, monitoreo y prueba real.
- READY_FOR_PRODUCTION: solo el owner puede autorizarlo despues de legal, backup/restore real, alertas, rollback, ambientes separados y evidencia completa.

## Bloqueos que obligan a detener construccion

- BLOCKED_BY_MISSING_CONTRACT: falta tabla, estado, permiso, endpoint, error, audit event o QA.
- BLOCKED_BY_CONTRACT_CONFLICT: dos documentos se contradicen.
- BLOCKED_BY_SECURITY_GAP: falta auth, RBAC, rate limit, secreto o proteccion de datos.
- BLOCKED_BY_PAYMENT_RISK: flujo de creditos o pago sin idempotencia, evidencia o reconciliacion.
- BLOCKED_BY_UI_CONTRACT_GAP: pantalla no define layout, copy, estado vacio, loading, error o permiso.

## Capacidad objetivo

El diseno debe soportar como minimo:

- 200 negocios registrados.
- 10,000 clientes.
- 2,000 ordenes activas/concurrentes.
- picos de busqueda, chat, reportes de pago y notificaciones.

Para lograrlo se requieren: Postgres con indices, pooling, Redis, colas, locks, idempotencia, workers separados, rate limits, monitoreo y pruebas de carga.
