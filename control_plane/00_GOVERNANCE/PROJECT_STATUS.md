# PROJECT_STATUS.md

Estado documental: READY_FOR_BUILDER_DOCS v0.3.

Estado de producto: PRE-BUILD.

Fecha de corte documental: 2026-07-03.

## Significado del estado

READY_FOR_BUILDER_DOCS significa que la documentacion contiene el mapa suficiente para que un builder empiece por slices con gobierno, reportes, limites, contratos y QA.

No significa que el producto este construido, probado, desplegado ni autorizado para uso real.

## Estados permitidos

- PRE-BUILD: no hay software final; solo documentos y contratos.
- READY_FOR_BUILDER: un slice tiene contrato suficiente para construirse.
- IN_BUILD: el builder esta implementando un slice aprobado.
- READY_FOR_OWNER_REVIEW: el slice fue construido y probado tecnicamente.
- READY_FOR_REAL_USE: solo el owner lo autoriza despues de deploy, monitoreo y prueba real.

## Bloqueos que obligan a detener construccion

- BLOCKED_BY_MISSING_CONTRACT: falta tabla, estado, permiso, endpoint, error, audit event o QA.
- BLOCKED_BY_CONTRACT_CONFLICT: dos documentos se contradicen.
- BLOCKED_BY_SECURITY_GAP: falta auth, RBAC, rate limit, secreto o proteccion de datos.
- BLOCKED_BY_PAYMENT_RISK: flujo de creditos o pago sin idempotencia, evidencia o reconciliacion.
- BLOCKED_BY_UI_CONTRACT_GAP: pantalla no define layout, copy, estado vacio, loading, error o permiso.

## Capacidad objetivo

El diseno debe soportar como minimo:

- 200 negocios verificados.
- 10,000 clientes.
- 2,000 ordenes activas/concurrentes.
- picos de busqueda, chat, reportes de pago y notificaciones.

Para lograrlo se requieren: Postgres con indices, pooling, Redis, colas, locks, idempotencia, workers separados, rate limits, monitoreo y pruebas de carga.
