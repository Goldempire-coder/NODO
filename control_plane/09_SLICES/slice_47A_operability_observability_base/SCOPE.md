# Slice 47A Scope

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Dentro Del Alcance

- Mapear observabilidad existente.
- Definir campos obligatorios: request, actor, surface, version, resource y resultado.
- Definir que se registra para flujos criticos.
- Definir que nunca se registra.
- Definir metricas de salud del usuario por flujo critico.
- Definir metricas base de costo por flujo sin exponer datos privados.
- Definir golden signals por superficie: trafico, errores, latencia y
  saturacion.
- Definir health checks profundos, no solo endpoint vivo.
- Proponer pruebas automaticas de redaccion y presencia de senales.
- Proponer smoke manual para Admin, Cliente y Negocio.

## Fuera Del Alcance

- Alertas, thresholds y campana operativa.
- Deteccion automatica de anomalias; solo se deja el contrato base.
- Jobs, cron, retries y reconciliacion.
- Cambios de infraestructura.
- Storage externo de logs.
- Nuevas migraciones sin aprobacion posterior.
- Cambios de reglas de negocio.

## Regla AFOS

Una senal cuenta solo si puede ser reproducida, consultada y relacionada con la
release exacta. Un `console.log` suelto no cuenta como observabilidad.
