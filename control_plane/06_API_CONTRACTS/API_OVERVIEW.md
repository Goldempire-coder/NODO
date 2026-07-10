# API_OVERVIEW.md

Contrato general para todas las APIs de NODO.

## Principios

- Backend FastAPI es la autoridad de permisos, estados, validaciones y auditoria.
- Frontend nunca decide si una accion esta permitida; solo consume capacidades devueltas por API.
- Todos los endpoints mutantes deben validar auth, RBAC, estado actual, ownership, idempotencia y audit event cuando aplique.
- Todos los endpoints deben responder con el ERROR_CONTRACT estandar.
- Health checks, webhooks publicos y `POST /api/v1/auth/telegram` son las unicas rutas sin sesion de usuario.
- Webhooks deben tener firma/secreto/rate limit.
- `POST /api/v1/auth/telegram` debe validar Telegram initData, aplicar rate limit y auditar intentos relevantes.

## Versionado

- Prefijo recomendado: `/api/v1`.
- Cambios breaking requieren nueva version o migration note.
- Campos obsoletos deben mantenerse por una ventana definida o bloquearse antes de construir.

## Headers obligatorios

- `Authorization: Bearer <session_jwt>` para rutas autenticadas.
- `Idempotency-Key` para crear orden, reportar pago, crear checkout Stripe, aprobar pago manual y ajustes admin.
- `X-Request-Id` generado por gateway/backend si no llega.
- `X-NODO-Surface` requerido por `GET /api/v1/surface/session` y recomendado para superficies separadas; no eleva permisos.

## Respuesta base

Exito:

```json
{
  "data": {},
  "request_id": "req_..."
}
```

Error:

```json
{
  "error": {
    "code": "ORDER_NOT_FOUND",
    "message": "No pudimos encontrar esta orden.",
    "details": {}
  },
  "request_id": "req_..."
}
```

## Grupos de endpoints

- AUTH_API: Telegram initData, sesion, refresh, logout.
- USERS_API: perfil, roles visibles, preferencias.
- BUSINESSES_API: perfil de negocio y endpoints legacy/internal de onboarding; Mini App Negocio no usa self-onboarding.
- ADS_API: anuncios, busqueda, ranking, disponibilidad.
- ORDERS_API: crear orden, detalle, historial, transiciones.
- PAYMENT_REPORTS_API: instrucciones, evidencia y reporte de pago del remitente.
- BUSINESS_ORDERS_API: operaciones del negocio sobre ordenes, confirmacion/rechazo de reporte, entrega y consumo de creditos.
- BUSINESS_PAYMENT_METHODS_API: lectura segura de metodos aprobados del negocio para selectores visuales; no permite IDs manuales ni gestion self-service en 14B.
- MESSAGES_API: mensajes, adjuntos privados y lectura de chat.
- DISPUTES_API: apertura, vista admin y resolucion admin de disputas en slice 09.
- CREDITS_API: wallet, ledger, Stripe checkout/webhook, pagos manuales, founder access y referrals.
- ADMIN_API: panel admin, aprobaciones, disputas, metricas, auditoria, job runs/admin ops y composicion de endpoints admin previos.
- SURFACE_SESSION_API: resolucion de superficie activa, capabilities por backend y gate canonico de Mini App Negocio/Admin Web.
- BUSINESS_INTAKE_API: Bot Registro Negocios y revision admin de solicitudes.
- SUPPORT_API: soporte general, soporte por orden, soporte negocio y cola admin/support.

## Idempotencia

La idempotencia debe guardar:

- key
- actor
- endpoint/action
- hash del payload
- resultado o referencia creada
- expiracion

Si la misma key llega con payload distinto, responder `IDEMPOTENCY_PAYLOAD_MISMATCH`.

## Webhooks

- Telegram webhook: validar secret token, rate limit, logs.
- Stripe webhook: validar firma, procesar event idempotente, nunca acreditar dos veces.
- Bot Registro Negocios webhook: `POST /api/v1/business-intake/telegram/webhook/{secret}`; validar secret derivado de `BUSINESS_INTAKE_BOT_TOKEN`, no aceptar `BOT_TOKEN`, no crear negocio activo, roles, access links, anuncios ni creditos desde webhook.
- Las rutas activas de creditos/referrals deben usar `/api/v1`; rutas legacy como `/credits/balance`, `/credit-purchases` y `/credit-purchases/:id/manual-proof` no son contrato valido.
- Webhooks deben responder rapido y delegar trabajo pesado a job.

## Paginacion

Listas usan cursor pagination. Prohibido offset sin justificacion en tablas calientes.

## Observabilidad

Cada request debe loggear request_id, actor anonimo/id interno, ruta, status, latencia y error code si falla. No loggear tokens, comprobantes completos ni datos bancarios completos.
