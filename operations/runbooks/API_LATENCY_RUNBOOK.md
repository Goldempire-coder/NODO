# RUNBOOK: API responds slowly

Estado de validacion: PARTIALLY VALIDATED

## SINTOMA

Pantallas tardan, Telegram Mini App se siente trabada, p95 alto.

## SEVERIDAD INICIAL

SEV-2 si afecta funciones principales.

## PRIMEROS CINCO MINUTOS

1. Confirmar `/ready`.
2. Revisar `X-NODO-Process-Time-Ms`.
3. Si marketplace es afectado, usar profiling staging solo en staging:
   ```powershell
   python scripts\capacity_real.py --help
   ```

## DIAGNOSTICO

- DB conexiones.
- Redis latencia.
- Railway CPU/memory.
- Endpoint especifico.
- Si es marketplace, revisar `_profile` bajo `ENABLE_STAGING_PROFILING=1`.

## INTERPRETACION DE CONCURRENCIA STAGING

Referencia oficial: `operations/STAGING_CONCURRENCY_POLICY.md`.

- c25/c50 son los niveles permitidos como gate de producto en staging.
- c50 es el maximo recomendado para gates de producto en staging actual.
- c100+ es probe de infraestructura/transporte, no gate de producto.
- c100+ no debe bloquear producto si `X-NODO-Process-Time-Ms`/`Server-Timing` muestran backend p95 bajo y el tiempo dominante esta en TTFB, `time_connect` o ruta externa.

Si `/api/v1/health`, `/api/v1/ready` o `/api/v1/version` muestran TTFB alto similar al endpoint afectado, no culpar el dominio de producto sin evidencia adicional.

Clasificar como transporte/ruta/edge/harness cuando:

- backend p95 permanece bajo;
- response size es pequena;
- TTFB domina client total;
- curl muestra `tcp_connect_p95` alto.

## MITIGACION

- Reducir stress externo.
- Revisar pool/workers.
- Rollback si coincide con deploy.

## VALIDACION

P95 vuelve al umbral definido.

## GAPS

Umbrales finales y dashboard no estan definidos.
