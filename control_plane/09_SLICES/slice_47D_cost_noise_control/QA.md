# Slice 47D QA

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Pruebas Esperadas

- Dashboard no refresca modulos ocultos innecesariamente.
- Pestana oculta pausa o reduce polling.
- Errores repetidos aplican backoff.
- No hay requests solapados para el mismo recurso.
- Requests iguales en curso se comparten o se justifica por que no se puede.
- Contadores criticos siguen actualizandose.
- No se pierden alertas de soporte o intake.
- Redis/DB calls bajan en prueba controlada.
- Cache local, si existe, no salta autorizacion ni guarda datos sensibles.
- Imagenes/adjuntos no se cargan hasta que son visibles o solicitados.
- Costo por flujo queda medido antes y despues del cambio.
- Metricas nuevas no usan etiquetas de alta cardinalidad.
- Logs de alto volumen tienen muestreo, nivel o retencion definidos.

## Smoke Manual

- Abrir Admin Web en una vista y esperar 2 minutos.
- Cambiar a otra pestana y volver.
- Crear ticket de soporte y confirmar que la alerta todavia llega.
