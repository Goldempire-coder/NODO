# Builder Prompt - Slice 47D

Actua como Builder senior de NODO bajo AFOS.

Skills a usar:
- performance-optimization
- observability-and-instrumentation
- frontend-ui-engineering
- security-and-hardening
- code-review-and-quality

Trabajo inicial:

1. Lee `COST_STRATEGY.md`.
2. Mapea polling y requests recurrentes en Admin, Cliente y Negocio.
3. Mapea llamadas Redis/DB/Storage afectadas.
4. Estima costo por usuario activo, negocio activo, orden, soporte, hora de
   Dashboard y dolar generado.
5. Identifica oportunidades de single-flight, request coalescing, cache local
   segura, lazy loading y compresion.
6. No modifiques archivos en la primera respuesta.
7. Identifica metricas o logs con riesgo de cardinalidad alta.
8. Entrega medicion estimada, riesgos de costo y plan minimo.

Prohibido:

- No cambiar proveedor.
- No reemplazar Redis/DB sin contrato separado.
- No cachear datos sensibles ni saltar autorizacion.
- No borrar evidencia.
- No reducir auditoria critica.
- No deploy ni produccion.
