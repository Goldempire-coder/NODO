# ADVANCED_SECURITY_BACKLOG.md

Backlog gobernado de seguridad avanzada para NODO.

Este documento no cambia el estado actual del producto ni autoriza `READY_FOR_REAL_USE`.
Su objetivo es dejar recordado que estos controles deben evaluarse antes de una fase de produccion publica mayor, auditoria externa, crecimiento sensible de volumen o manejo de riesgo elevado.

## Estado actual

```txt
ADVANCED_SECURITY_BACKLOG_CREATED
```

NODO ya tiene controles base para staging controlado:

- auth JWT y refresh controlado
- validacion Telegram initData en backend
- RBAC y ownership backend
- Redis rate limits
- idempotencia en mutaciones criticas
- audit logs
- errores seguros
- storage privado con signed URLs
- Stripe webhook firmado
- secretos fuera del frontend y fuera del repo

Estos controles NO equivalen a una arquitectura enterprise completa.

## Controles avanzados pendientes

| Control | Estado | Prioridad | Nota |
| --- | --- | --- | --- |
| Zero Trust | pendiente | alta | Usar para admin, staging y accesos internos antes de produccion publica amplia. |
| API Gateway / edge WAF | pendiente | alta | Preferido como primera capa: Cloudflare, reglas de rate limit, WAF, bot protection y allowlists. |
| Runtime secret injection | parcial | alta | Hoy se usan env vars/local secrets. En deploy debe quedar por ambiente en proveedor, sin secretos en repo ni frontend. |
| Rotacion de secretos | pendiente | alta | Primero runbook manual probado; luego automatizacion. |
| Credenciales de corta duracion | parcial | media | JWT y signed URLs son cortos; DB/Redis/Supabase/Stripe siguen usando secretos estaticos. |
| Firma HMAC | parcial | media | Existe en Telegram/Stripe/JWT. Evaluar firma de webhooks internos o jobs sensibles. |
| Firma Ed25519 | pendiente | baja/media | Evaluar solo si hay necesidad de firmas asimetricas entre servicios o integraciones externas. |
| Firma de codigo / build provenance | pendiente | media | Evaluar antes de produccion publica: commits firmados, artifacts firmados, provenance/SBOM. |
| Canary tokens | pendiente | media | Agregar tokens trampa para detectar exposicion de secretos o acceso indebido. |
| HSM/KMS | pendiente | baja/media | No requerido para staging. Evaluar si el riesgo/regulacion/costo lo justifica. |
| mTLS | pendiente | baja/media | Evaluar si hay multiples servicios internos propios. No prioritario con arquitectura simple inicial. |
| RASP | pendiente | baja | No prioritario para MVP; considerar solo con presupuesto y threat model mas maduro. |
| eBPF runtime security | pendiente | baja | Normalmente gestionado por plataforma/infra. Evaluar en infraestructura propia o Kubernetes. |
| Service mesh | pendiente | baja | No recomendado en etapa inicial; agrega complejidad si no hay microservicios. |

## Orden recomendado

### Fase A - antes de staging publico amplio

1. Cloudflare delante de frontend/API.
2. WAF y reglas de rate limit en edge.
3. Zero Trust para admin y ambientes internos.
4. Secretos por ambiente en runtime provider.
5. Runbook manual de rotacion de secretos.
6. Monitoreo de errores, auth failures, rate limit hits, storage failures y webhooks.

### Fase B - antes de produccion publica fuerte

1. Rotacion periodica de secretos con evidencia.
2. Canary tokens para secretos criticos.
3. Firma de commits/build artifacts o provenance.
4. SBOM y escaneo de dependencias.
5. Politicas estrictas de deploy y rollback.

### Fase C - solo si la escala/riesgo lo justifica

1. HSM/KMS.
2. mTLS entre servicios internos.
3. eBPF runtime security.
4. RASP.
5. Service mesh.
6. Ed25519 para integraciones o firmas entre servicios.

## Regla para Builder

Builder NO debe implementar estos controles sin un slice o contrato explicito aprobado por owner.

Si una tarea futura pide activar cualquiera de estos controles, Builder debe responder primero con un `BUILDER_UNDERSTANDING_REPORT` que incluya:

- control exacto a implementar
- proveedor/herramienta propuesta
- secretos involucrados
- impacto en deploy
- impacto en costos
- plan de rollback
- pruebas de seguridad esperadas
- evidencia que demostrara que quedo activo

## No usar como bloqueo retroactivo

Este backlog no invalida los slices ya construidos ni los estados `READY_FOR_OWNER_REVIEW`.

Solo se vuelve bloqueante cuando el owner apruebe un slice futuro de seguridad avanzada, deploy final o produccion publica con estos controles como requisito.
