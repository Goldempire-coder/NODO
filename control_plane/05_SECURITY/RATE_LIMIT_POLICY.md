# RATE_LIMIT_POLICY.md

## Slice 14 - Surface, bot and support limits

- `GET /api/v1/surface/session`: per user/session.
- Bot intake start/submit/upload: per Telegram user/chat/contact.
- Business intake admin accept/reject: per admin actor.
- Support ticket create/message/upload: per actor and ticket.
- Support admin list/detail: per admin/support actor.
- Support assignment/escalation/resolve/close and attachment view-url: per support/admin actor and ticket.
- In-memory limits are allowed only in test environment; runtime normal uses Redis.
- Excepcion runtime aprobada: `GET /api/v1/ads/search` puede usar limite local por proceso porque es lectura publica de marketplace, no revela datos sensibles completos, no muta estado y queda protegido adicionalmente por cache corto y controles de infraestructura. Rutas sensibles y mutaciones siguen usando Redis.

Contrato de rate limits y abuso.

## Objetivo

Reducir abuso, spam, fuerza bruta, scraping, duplicaciones por retry y ataques de denegacion basicos.

## Regla madre

Toda ruta sensible debe tener rate limit en backend. El frontend no cuenta como defensa.

## Dimensiones minimas

Aplicar limites por combinacion segun endpoint:

```txt
ip
telegram_user_id
business_id
order_id
route
action_type
```

## Rutas sensibles

- auth/initData login
- crear orden
- extender timer de pago
- reportar pago
- subir evidencia
- revelar datos de pago
- listar/detallar ordenes de negocio
- confirmar pago recibido por negocio
- rechazar reporte de pago por negocio
- marcar pago movil enviado por negocio
- enviar mensajes de chat
- subir adjuntos de mensajes
- abrir disputa
- listar/ver disputas admin
- resolver disputas admin
- crear anuncio
- pausar/archivar anuncio
- crear checkout Stripe
- enviar pago manual Zelle/USDT
- subir/ver comprobante manual de compra de creditos
- aplicar codigo de referido
- consultar referrals propios
- webhook Stripe, ademas de verificacion de firma e idempotencia
- admin approvals/rejections
- admin credit adjustments
- admin user search/detail reads
- admin user suspend/reactivate/block
- admin business access link reads/mutations
- admin metrics/audit log reads
- admin job run reads
- admin job dry-run execution
- consultar metodos de pago propios aprobados del negocio
- crear compra Base USDC de creditos
- enviar tx hash para compra Base USDC
- consultar status de compra on-chain cuando se use polling
- admin review de compra on-chain
- watcher/dry-run on-chain si se expone por API/admin
- crear/listar/detallar tickets de soporte
- responder ticket de soporte
- subir adjunto de soporte
- asignar/escalar/resolver/cerrar ticket de soporte
- generar signed URL de adjunto de soporte
- listar/ver staff interno
- crear invitacion staff
- activar/suspender/revocar staff
- actualizar permisos staff
- ver actividad staff

## Reglas funcionales

- Usar Redis para contadores y ventanas en rutas sensibles y mutaciones.
- `GET /api/v1/ads/search` puede usar throttle local por proceso para evitar que cada busqueda pague latencia externa de Redis.
- Devolver error estable `RATE_LIMITED`.
- No filtrar informacion sensible en el error.
- Loggear evento de abuso si el limite se repite.
- Rate limit no reemplaza RBAC ni idempotencia.

## Cooldowns de negocio

Negocios con repetidas disputas, no respuesta o reportes deben poder entrar en:

```txt
risk_level = watch | under_review | restricted | high_risk
```

## Cooldowns de remitente

Remitentes con ordenes abandonadas repetidas pueden tener cooldown temporal para crear nuevas ordenes.

## Tests obligatorios

- limite por IP en auth.
- limite por usuario en create_order.
- limite por negocio en create_ad.
- limite por negocio/usuario en `GET /api/v1/business/payment-methods`.
- limite por order_id en report_payment.
- limite en admin critical actions.
- error `RATE_LIMITED` sin stack trace ni datos internos.

## Bloqueo

Si una ruta sensible queda sin limite, Builder debe reportar:

```txt
BLOCKED_BY_SECURITY_GAP
```

## Observability ingest - slice 24

`POST /api/v1/observability/events` must be rate-limited by:

- user id when authenticated;
- session_id;
- IP hash;
- surface.

Contract limits:

- max 20 events per batch;
- max 2048 bytes per event;
- max 64 KB request body;
- max 500 persisted events per session per day;
- minimum 5 seconds between normal batches per session.

Rate limit failures return `OBSERVABILITY_RATE_LIMITED` without exposing internals.
