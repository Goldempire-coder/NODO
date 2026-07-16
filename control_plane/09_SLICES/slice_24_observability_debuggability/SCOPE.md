# SCOPE - slice_24_observability_debuggability

## Construir en futura build

- Middleware backend de request logging estructurado.
- Propagacion de `request_id`, `correlation_id` y `operation_id`.
- Helper de redaccion reutilizable para logs, events y errores.
- Frontend breadcrumbs seguros por superficie.
- Session replay estructurado sin video en modo local ring buffer y, si esta habilitado por env, ingestion backend.
- Endpoint backend de ingestion de eventos observability.
- Consulta Admin Web de eventos diagnosticos con RBAC y masking.
- Job de cleanup por retencion.
- Tests de privacidad, redaccion, rate limit y correlacion.

## No construir

- Proveedores externos como Sentry, Datadog, New Relic, LogRocket u OpenTelemetry SaaS.
- Video replay, grabacion de pantalla o captura de DOM completo.
- Captura de payloads privados, documentos, mensajes completos, signed URLs o tokens.
- Observability como ledger financiero.
- Audit formal como session replay.
- Cambios a reglas de negocio, ordenes, creditos, anuncios, soporte, staff, bots o disputas.
- Deploy.
- `READY_FOR_REAL_USE`.

## Entornos permitidos iniciales

- Local: permitido con `OBSERVABILITY_MODE=local_only`.
- Staging: permitido con `OBSERVABILITY_INGEST_ENABLED=1` y limites activos.
- Production: deshabilitado por defecto. Cualquier activacion de persistencia en produccion requiere aprobacion owner posterior.
