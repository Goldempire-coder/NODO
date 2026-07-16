# slice_24_observability_debuggability

Estado contractual: `READY_FOR_OWNER_APPROVAL_TO_BUILD_24`.

Objetivo: construir observabilidad segura y depurable para NODO sin inventar proveedores externos, sin capturar datos sensibles innecesarios y sin mezclar audit formal con diagnostico operacional.

Este slice responde al bloqueo `BLOCKED_BY_MISSING_CONTRACT` detectado en la auditoria de observabilidad. Cierra contratos para:

- modelo canonico de correlacion;
- request logging estructurado;
- breadcrumbs frontend;
- session replay estructurado sin video;
- ingestion de eventos frontend;
- retencion y cleanup;
- redaccion obligatoria;
- limites de costo;
- acceso Admin Web/support;
- diferencia entre audit formal y observability operacional.

No autoriza deploy ni `READY_FOR_REAL_USE`.
