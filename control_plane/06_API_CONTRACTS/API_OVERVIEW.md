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
- BUSINESS_ORDERS_API: operaciones del negocio sobre ordenes, confirmacion de pago, apertura de disputa por problema, entrega y consumo de creditos.
- BUSINESS_PAYMENT_METHODS_API: lectura segura de metodos aprobados del negocio para selectores visuales; no permite IDs manuales ni gestion self-service en 14B.
- BUSINESS_SECURITY_API: PIN operativo de Mini App Negocio para configurar, verificar, bloquear y consultar el estado de desbloqueo antes de mutaciones sensibles.
- MESSAGES_API: mensajes, adjuntos privados y lectura de chat.
- DISPUTES_API: apertura, vista admin y resolucion admin de disputas en slice 09.
- CREDITS_API: wallet, ledger, Stripe checkout/webhook, pagos manuales, Base USDC on-chain credit topups, founder access y referrals.
- ADMIN_API: panel admin, aprobaciones, disputas, metricas, auditoria, job runs/admin ops, control de usuarios/access links y composicion de endpoints admin previos.
- SURFACE_SESSION_API: resolucion de superficie activa, capabilities por backend y gate canonico de Mini App Negocio/Admin Web.
- BUSINESS_INTAKE_API: Bot Registro Negocios y revision admin de solicitudes.
- SUPPORT_API: soporte general, soporte por orden/anuncio/credito, mensajes, adjuntos privados y cola admin/support.
- STAFF_API: delegacion interna de empleados/colaboradores, staff profiles, permisos, invitaciones y actividad limitada en Admin Web.
- OBSERVABILITY_API: request logging, correlation ids, frontend breadcrumbs/session replay estructurado sin video, ingestion redaccionada y busqueda Admin Web con TTL.

## Idempotencia

La idempotencia debe guardar:

- key
- actor
- endpoint/action
- hash del payload
- resultado o referencia creada
- expiracion

Si la misma key llega con payload distinto, responder `IDEMPOTENCY_PAYLOAD_MISMATCH`.

Mutaciones admin de usuarios/access links requieren `Idempotency-Key`, reason y audit.

Mutaciones staff internas requieren `Idempotency-Key`, reason, backend RBAC y audit.

## PIN operativo de negocio

La Mini App Negocio debe usar estos endpoints para proteger acciones sensibles:

- `GET /api/v1/business/security/pin`
- `POST /api/v1/business/security/pin/setup`
- `POST /api/v1/business/security/pin/verify`
- `POST /api/v1/business/security/pin/lock`

Reglas:

- El PIN pertenece al `business_access_link`, no al dispositivo ni al frontend.
- El backend guarda hash, no PIN en claro.
- Crear/editar metodos de pago, publicar/editar/pausar/reactivar/republicar
  anuncios, comprar creditos, aplicar referidos y confirmar/reportar
  problema/entregar ordenes requieren PIN configurado y desbloqueado.
- Si el PIN falta, esta bloqueado o no esta desbloqueado, las mutaciones sensibles responden `423` con codigo `BUSINESS_PIN_NOT_SET`, `BUSINESS_PIN_LOCKED` o `BUSINESS_PIN_REQUIRED`.
- Intentos invalidos responden `BUSINESS_PIN_INVALID`, incrementan contador seguro y pueden bloquear temporalmente el link.
- Logs y audit events nunca deben contener el PIN en claro.

## Webhooks

- Telegram webhook: validar secret token, rate limit, logs.
- Stripe webhook: validar firma, procesar event idempotente, nunca acreditar dos veces.
- On-chain credit verifier/watcher: no es webhook publico; valida Base USDC por RPC/backend, nunca acredita por frontend, screenshot o texto libre.
- Bot Registro Negocios webhook: `POST /api/v1/business-intake/telegram/webhook/{secret}`; validar secret derivado de `BUSINESS_INTAKE_BOT_TOKEN`, no aceptar `BOT_TOKEN`, no crear negocio activo, roles, access links, anuncios ni creditos desde webhook.
- Las rutas activas de creditos/referrals deben usar `/api/v1`; rutas legacy como `/credits/balance`, `/credit-purchases` y `/credit-purchases/:id/manual-proof` no son contrato valido.
- Webhooks deben responder rapido y delegar trabajo pesado a job.

## Paginacion

Listas usan cursor pagination. Prohibido offset sin justificacion en tablas calientes.

## Observabilidad

Cada request debe loggear request_id, actor anonimo/id interno, ruta, status, latencia y error code si falla. No loggear tokens, comprobantes completos ni datos bancarios completos.

Slice 24 amplia este contrato:

- `X-Request-Id`, `X-Correlation-Id`, `X-NODO-Operation-Id` y `X-NODO-Surface` son headers canonicos de diagnostico.
- Las rutas deben loggear route template, no URL cruda con query sensible.
- `POST /api/v1/observability/events` queda contratado solo para eventos redaccionados y env-gated.
- Admin/support consulta observability via RBAC y masking.
