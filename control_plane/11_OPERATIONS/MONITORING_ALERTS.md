# MONITORING_ALERTS.md

Monitoreo minimo para operar NODO sin ceguera.

## Metricas API

- request count por ruta.
- status code rate.
- p50/p95/p99 latency.
- error rate 4xx/5xx.
- rate limit hits.
- auth failures.

## Metricas dominio

- ordenes creadas.
- ordenes expiradas.
- reportes de pago.
- confirmaciones de pago.
- entregas.
- disputas abiertas.
- disputas resueltas.
- creditos comprados.
- creditos acreditados.
- rechazos manuales.

## Metricas jobs

- job queue depth.
- job failures.
- retries.
- lock contention.
- webhook lag.
- notification failures.

## Alertas criticas

- 5xx sostenidos.
- bot webhook failures.
- Stripe webhook failures.
- doble intento de acreditacion.
- balance negativo rechazado.
- job failures repetidos.
- upload failures.
- storage signed URL failures.
- disputes spike.
- admin login failures.
- DB connections cerca del limite.
- Redis unavailable.

## Logs

Logs deben incluir request_id, actor interno, ruta, status, latencia y error code. Prohibido loggear tokens, secretos, comprobantes completos o datos bancarios completos.

## Dashboard minimo

- salud API.
- salud worker.
- salud DB.
- salud Redis.
- ordenes activas.
- pagos pendientes.
- disputas abiertas.
- creditos pendientes manuales.
- errores ultimas 24h.
