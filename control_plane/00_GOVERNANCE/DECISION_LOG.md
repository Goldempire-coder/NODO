# DECISION_LOG.md

Este archivo registra decisiones aprobadas por el owner. Si otro documento contradice estas decisiones, prevalece SOURCE_OF_TRUTH y luego este decision log.

## Decisiones aprobadas

| Fecha | Decision | Estado |
| --- | --- | --- |
| 2026-07-08 | Slice 14D2 usa bot Telegram separado para intake de negocios con `BUSINESS_INTAKE_BOT_TOKEN`, webhook canonico `POST /api/v1/business-intake/telegram/webhook/{secret}`, pasos conversacionales canonicos en `last_step`, persistencia parcial por respuesta valida, idempotencia por `telegram_chat_id + update_id`, documentos descargados desde Telegram a storage privado y prohibicion de crear negocio activo, roles, access links, anuncios, creditos o acceso a Mini App Negocio. | aprobado |
| 2026-07-05 | Stack de staging/produccion inicial aprobado: Cloudflare Pages frontend, Railway backend/workers, Supabase Pro PostgreSQL, Upstash Redis, Cloudflare R2 o Supabase Storage, Stripe test/live segun gate y Telegram webhook. Vercel queda legacy/no recomendado para NODO por costo de escala. | aprobado |
| 2026-07-04 | Slice 10 usa `job_runs.job_type` como columna canonica; `job_name` queda prohibido/no valido. `job_type` inicial: `expire_and_escalate_orders`. | aprobado |
| 2026-07-04 | Slice 10 define enums canonicos `job_runs.status = started/finished/failed/skipped/lock_not_acquired` y `notification_jobs.status = pending/sent/failed/skipped/cancelled`. | aprobado |
| 2026-07-04 | Slice 10 usa `notification_jobs.notification_type` y `dedupe_key`; `event_type`/`telegram_chat_id` quedan legacy/no validos para nuevas migraciones de notification jobs. | aprobado |
| 2026-07-04 | Slice 10 incluye endpoints admin/ops protegidos para `job_runs` y dry-run; support es read-only y dry-run nunca muta datos reales. | aprobado |
| 2026-07-04 | Slice 10 no construye `R-10_CONFIRM_RECEIVED`; solo puede auto-completar por timer `delivered -> completed` con `completion_reason = auto_completed_after_24h`. | aprobado |
| 2026-07-04 | Slice 09 `slice_09_admin_console` incluye resolucion admin de disputas mediante `POST /api/v1/admin/disputes/{id}/resolve`; admin/super_admin pueden resolver, support queda read-only. | aprobado |
| 2026-07-04 | `dispute.resolution_type` canonico para slice 09 usa `remitter_favored`, `business_favored`, `cancelled`, `completed` y `keep_under_review`; no se crean alias nuevos sin actualizar enums. | aprobado |
| 2026-07-04 | La resolucion admin de disputa en slice 09 define efectos explicitos sobre `orders`, `disputes`, `credit_wallets`, `credits_ledger` y `ad.status`; NODO no recibe, retiene, transfiere ni garantiza fondos. | aprobado |
| 2026-07-04 | Metricas admin de slice 09 son read model calculado desde tablas existentes; no se crea tabla `system_metrics` en MVP. | aprobado |
| 2026-07-04 | Slice 09 puede enlazar o componer A-04, A-05 y A-13, pero esas pantallas y su logica siguen perteneciendo a `slice_08_credits_referrals`. | aprobado |
| 2026-07-04 | Slice 08 usa solo rutas activas bajo `/api/v1`; rutas legacy `/credits/balance`, `/credit-purchases` y `/credit-purchases/:id/manual-proof` quedan no validas. | aprobado |
| 2026-07-04 | Stripe puede iniciar checkout, pero solo webhook Stripe con firma valida acredita creditos; redirect frontend nunca acredita y webhook debe ser idempotente por event/session/status/ledger/idempotency. | aprobado |
| 2026-07-04 | Pagos manuales de creditos quedan `pending_manual_review`; admin/super_admin aprueba o rechaza con reason, y solo aprobacion acredita. | aprobado |
| 2026-07-04 | Comprobantes manuales de creditos usan `file_assets.resource_type = credit_purchase`, `file_type = credit_purchase_proof`, storage privado y no exponen `storage_path`. | aprobado |
| 2026-07-04 | Founder access usa campos canonicos en `businesses`; `founder_access` no es tabla activa MVP. | aprobado |
| 2026-07-04 | Referrals usan `referral_codes` y `referral_events`; tabla `referrals` queda legacy/no valida para nuevas migraciones. | aprobado |
| 2026-07-04 | `refund` y `adjustment` no son tipos activos de `credits_ledger`; usar `release` y `admin_adjustment`. | aprobado |
| 2026-07-03 | El producto se construye para uso masivo, no como demo/piloto. | aprobado |
| 2026-07-03 | Capacidad objetivo inicial: 200 negocios, 10,000 clientes, 2,000 ordenes activas/concurrentes. | aprobado |
| 2026-07-03 | Stack base: Next.js, TypeScript, Tailwind, Telegram Mini App SDK/UI, FastAPI, PostgreSQL/Supabase, Redis. | aprobado |
| 2026-07-03 | Frontend en Vercel; backend en runtime dedicado production-grade; Telegram por webhook. Reemplazado el 2026-07-05 por Cloudflare Pages + Railway como stack inicial aprobado. | reemplazado |
| 2026-07-03 | Stripe es la pasarela principal para compra automatica de creditos de negocio. | aprobado |
| 2026-07-03 | Zelle y USDT TRC20 quedan como compra manual de creditos con comprobante y aprobacion admin. | aprobado |
| 2026-07-03 | Fundadores tienen 30 dias gratis dentro de limites de riesgo; no es ilimitado sin control tecnico. | aprobado |
| 2026-07-03 | Admin requiere panel funcional completo; no basta whitelist por Telegram ID. | aprobado |
| 2026-07-03 | UI visual basada en referencias oscuras fintech con logo NODO, cards compactas, CTA verde/azul, Zelle morado y USDT verde. | aprobado |
| 2026-07-03 | NODO no es escrow, no guarda fondos y no garantiza entrega; solo verifica, registra, audita y facilita conexion. | aprobado |
| 2026-07-03 | Builder debe usar arquitectura modular profesional y revisar lineas antes de cortar. | aprobado |
| 2026-07-03 | Un anuncio solo puede tener 1 orden activa en MVP; al crear orden pasa a `in_order` y sale del catalogo. | aprobado |
| 2026-07-03 | `under_review` no va en `verification_status`; va en `risk_level` como control interno. | aprobado |
| 2026-07-03 | Pausar anuncio no congela `expires_at`; los 7 dias siguen corriendo. | aprobado |
| 2026-07-03 | MVP usa roles persistentes `remitter`, `business_owner`, `admin`, `super_admin`, `support`; `business_operator` y `support_readonly` quedan post-MVP. | aprobado |
| 2026-07-03 | Mantener `trust_level` y `risk_level` separados: reputacion comercial vs control interno. | aprobado |
| 2026-07-03 | Para RBAC, `super_admin` es rol persistente permitido; `guest` es actor derivado/no persistente para requests sin sesion. | aprobado |
| 2026-07-03 | `business` queda prohibido como rol persistente; el rol canonico es `business_owner`. | aprobado |
| 2026-07-03 | `audit_logs` usa `resource_type/resource_id`, no `entity_type/entity_id`, e incluye `request_id` y `job_id` cuando aplique. | aprobado |
| 2026-07-03 | `slice_00_foundation` debe crear columnas base explicitas para `users`, `audit_logs`, `job_runs` y `app_metadata`; health checks no guardan cada resultado en DB. | aprobado |
| 2026-07-03 | Auth Telegram usa endpoints canonicos `/api/v1/auth/telegram`, `/api/v1/auth/refresh`, `/api/v1/auth/logout` y `/api/v1/users/me`; queda prohibido `/auth/telegram-login`. | aprobado |
| 2026-07-03 | `slice_01_auth_telegram` usa tabla `sessions` con `refresh_token_hash`; no se usa `session_revocations` en MVP. | aprobado |
| 2026-07-03 | Refresh token nunca se guarda plano; se guarda hash, se rota en refresh y logout revoca la sesion. | aprobado |
| 2026-07-03 | Para `slice_02_business_verification`, `pending` reemplaza cualquier uso de `pending_review` en verificacion de negocio. | aprobado |
| 2026-07-03 | `draft` queda permitido solo como estado UI/workflow previo; no es `business.verification_status`. | aprobado |
| 2026-07-03 | `slice_02_business_verification` incluye uploads privados de documentos de verificacion usando `file_assets`; no hay documentos publicos ni storage paths expuestos. | aprobado |
| 2026-07-03 | `business_verification_submissions` queda como tabla oficial con business_id, submitted_by_user_id, status, submitted_data_json, admin_reviewed_by_user_id, admin_reason, submitted_at, reviewed_at, created_at y updated_at. | aprobado |
| 2026-07-04 | Rutas canonicas de ads/marketplace para slice 03: `GET /api/v1/ads/search`, `GET /api/v1/ads/{id}`, `POST /api/v1/business/ads`, `GET /api/v1/business/ads`, `GET /api/v1/business/ads/archived`, `PUT /api/v1/business/ads/{id}`, `POST /api/v1/business/ads/{id}/pause`, `POST /api/v1/business/ads/{id}/archive`. | aprobado |
| 2026-07-04 | B-09 y B-10 usan endpoints separados: `/api/v1/business/ads` para operativos y `/api/v1/business/ads/archived` para historicos archivados/expirados. | aprobado |
| 2026-07-04 | `credits_ledger` canonico incluye reason, source, reference_type y reference_id; `notes` queda opcional y no reemplaza `reason`. | aprobado |
| 2026-07-04 | Slice 03 usa expiracion pasiva/materializada de anuncios; search excluye vencidos y el worker masivo queda para `slice_10_jobs_notifications`. | aprobado |
| 2026-07-04 | `credit_wallets` puede crearse lazy/idempotente en slice 03 para negocios aprobados si falta; se crea con balances cero y no acredita creditos. | aprobado |
| 2026-07-04 | Rutas canonicas de ordenes para slice 04: `POST /api/v1/orders`, `GET /api/v1/orders/{id}`, `GET /api/v1/orders/mine`, `POST /api/v1/orders/{id}/extend-payment-deadline`, `POST /api/v1/orders/{id}/cancel`. Rutas legacy `/orders` quedan prohibidas como API contract. | aprobado |
| 2026-07-04 | `POST /api/v1/orders` persiste directamente `order.status = waiting_payment`; `created` queda solo como audit/state event, no como estado final persistente del endpoint. | aprobado |
| 2026-07-04 | Slice 04 usa `orders.idempotency_key` con unique parcial por `remitter_user_id + idempotency_key`; no usa tabla separada de idempotencia. | aprobado |
| 2026-07-04 | Slice 04 guarda `payment_instructions_snapshot` privado al crear orden, pero create/detail/list no revelan instrucciones completas; slice 05 las revela con `GET /api/v1/orders/{id}/payment-instructions`. | aprobado |
| 2026-07-04 | Slice 04 incluye cancelacion de orden propia solo en `waiting_payment` antes de reporte de pago y extension unica de 15 minutos; reporte de pago, confirmacion del negocio, entrega, chat y disputas quedan fuera. | aprobado |
| 2026-07-04 | Rutas canonicas de slice 05: `GET /api/v1/orders/{id}/payment-instructions`, `POST /api/v1/orders/{id}/payment-evidence`, `POST /api/v1/orders/{id}/payment-report`; queda prohibida la ruta legacy `POST /orders/:id/payment-report`. | aprobado |
| 2026-07-04 | Slice 05 revela instrucciones completas solo al remitente dueno, setea `payment_data_revealed_at/payment_data_revealed_by`, audita `payment_instructions_viewed` y no crea reportes desde el endpoint de reveal. | aprobado |
| 2026-07-04 | Slice 05 usa `file_assets` como tabla canonica para evidencia privada de pago con `resource_type = payment_report` y `file_type = payment_evidence`; no crea `payment_evidence_files` ni `storage_objects`. | aprobado |
| 2026-07-04 | `payment_reports` queda como tabla oficial del reporte del remitente con status inicial `submitted`, idempotency_key, payment_type, referencias por metodo, proof_file_id, payload hash, timestamps y constraints por Zelle/USDT TRC20. | aprobado |
| 2026-07-04 | Para evidencia Zelle previa al reporte, `POST /payment-evidence` puede reservar `pending_payment_report_id`; `POST /payment-report` debe crear `payment_reports.id = pending_payment_report_id` al usar ese comprobante. | aprobado |
| 2026-07-04 | Reportar pago mueve `waiting_payment -> payment_reported`, mantiene ad `in_order`, mantiene creditos bloqueados y no consume creditos, no confirma negocio, no entrega pago movil ni completa orden. | aprobado |
| 2026-07-04 | Rutas canonicas de operaciones de negocio sobre ordenes para slice 06: `GET /api/v1/business/orders`, `GET /api/v1/business/orders/{id}`, `POST /api/v1/business/orders/{id}/confirm-payment`, `POST /api/v1/business/orders/{id}/reject-payment-report`, `POST /api/v1/business/orders/{id}/mark-delivered`. | sustituido parcialmente por C0 2026-08-09 |
| 2026-07-04 | El rechazo de reporte de pago en slice 06 es canonico como `payment_reported -> payment_rejected`; no vuelve automaticamente a `waiting_payment`. | sustituido por C0 2026-08-09 |
| 2026-07-04 | Al rechazar reporte, `payment_reports.status = rejected`, creditos siguen bloqueados, `ad.status = in_order` y el anuncio no vuelve automaticamente al marketplace. | sustituido por C0 2026-08-09 |
| 2026-07-04 | Confirmar pago recibido en slice 06 cambia `payment_reported -> payment_confirmed`, marca `payment_reports.status = accepted`, setea deadlines de entrega y consume creditos bloqueados exactamente una vez mediante ledger `consume`. | aprobado |
| 2026-07-04 | Marcar entregado en slice 06 cambia `payment_confirmed -> delivered`, setea timers de auto-complete, pero no completa la orden ni confirma recepcion del cliente. | aprobado |
| 2026-07-04 | En slice 06, cuando el negocio confirma pago recibido, `ad.status = archived`; la orden sigue viva para entrega, disputa o cierre futuro, pero el anuncio ya cumplio su funcion y no vuelve al marketplace. | aprobado |
| 2026-07-04 | Slice 07 queda limitado a chat, adjuntos privados y apertura/vista basica de disputas; R-10 confirm received, completion, rating, auto-complete y resolucion admin completa quedan para slice futuro. | aprobado |
| 2026-07-04 | La tabla canonica de mensajes es `messages`; `chat_messages` queda como nombre legacy/no valido para nuevas migraciones y contratos activos. | aprobado |
| 2026-07-04 | Eventos audit canonicos de slice 07: `message_created`, `message_attachment_uploaded`, `dispute_opened`, `dispute_message_created`; `message_sent` no es evento audit canonico y `message_blocked` no pertenece a slice 07. | aprobado |
| 2026-07-04 | Abrir disputa en slice 07 mueve `orders.status = disputed`, guarda `previous_order_status`, crea `disputes.status = open`, crea `dispute_events` y no resuelve creditos/anuncios; desde `payment_reported/payment_rejected` mantiene creditos bloqueados y ad `in_order`, desde `payment_confirmed/delivered` mantiene creditos consumidos y ad `archived`. | aprobado |
| 2026-07-04 | Adjuntos de mensajes en slice 07 usan `file_assets` con `resource_type = message`, `file_type = message_attachment`, storage privado, MIME permitido `image/jpeg`, `image/png`, `image/webp`, `application/pdf`, maximo 5 MB y nunca exponen `storage_path`. | aprobado |
| 2026-07-04 | En slice 07, admin/super_admin/support pueden ver disputas segun RBAC, pero no resolverlas; `resolve_dispute`, `POST /api/v1/admin/disputes/{id}/resolve` y el audit `dispute_resolved` quedan fuera de slice 07 y reservados para `slice_09_admin_console`. | aprobado |
| 2026-07-05 | Se crea `control_plane/05_SECURITY/ADVANCED_SECURITY_BACKLOG.md` como recordatorio gobernado de controles post-staging: Zero Trust, API gateway/WAF, runtime secret injection, rotacion de secretos, credenciales cortas, HMAC/Ed25519, HSM/KMS, mTLS, RASP, canary tokens, eBPF, service mesh y firma de codigo. No bloquea retroactivamente slices ya aceptados ni declara `READY_FOR_REAL_USE`. | aprobado |

## 2026-07-21 - Slice 42A business reputation foundation

| Fecha | Decision | Estado |
|---|---|---|
| 2026-07-21 | `trust_level` queda reservado para limites/capacidad interna; la reputacion visible usa `reputation_tier`. Esta decision sustituye la interpretacion de reputacion comercial registrada el 2026-07-03, sin renombrar ni eliminar `trust_level`. | aprobado |
| 2026-07-21 | `risk_level` es interno y nunca se expone en DTOs publicos o marketplace. Una restriccion se comunica como indisponibilidad neutral, sin revelar `under_review`. | aprobado |
| 2026-07-21 | Rating MVP usa solo estrellas 1..5, una vez por orden completada y sin comentarios o resenas textuales. Admin no puede falsificar ratings. | aprobado |
| 2026-07-21 | Success rate, promedios y tier se calculan exclusivamente en backend desde datos reconstruibles; frontend solo presenta los valores recibidos. | aprobado |
| 2026-07-21 | Tiers de reputacion: `new`, `active`, `reliable`, `elite`, con minimos aprobados de ordenes, ratings, promedio y success rate. Pausado/Offline y No disponible son estados de disponibilidad, no tiers persistidos. | aprobado |

## Decisiones rechazadas o prohibidas

- Admin MVP solo por whitelist sin panel funcional.
- Bot por polling en produccion.
- Creditos como comision/spread por transaccion.
- Promesas de fondos garantizados, escrow, dinero protegido, transaccion garantizada, entrega garantizada.
- UI generica tipo landing page.
- Funciones Frankenstein mezclando permisos, queries, logica, auditoria y response.
- Estados inventados fuera de ENUMS_AND_STATUS_MASTER.
- Multiples ordenes activas sobre un mismo anuncio en MVP.
- Usar `under_review` como `verification_status`.
- Pausar/reactivar para extender vida de anuncio sin renovar.
- Usar `business` como `user.role`.
- Usar `entity_type/entity_id` en audit logs nuevos.
- Usar `POST /auth/telegram-login` como endpoint auth.
- Guardar refresh token plano.
- Usar `pending_review` como `business.verification_status`.
- Usar `draft` como `business.verification_status`.
- Usar rutas legacy de anuncios como `POST /ads`, `GET /ads/:id` o `PATCH /ads/:id/pause` fuera del prefijo canonico `/api/v1`.
- Usar rutas legacy de ordenes como `POST /orders`, `GET /orders/:id`, `POST /orders/:id/extend` o `POST /orders/:id/cancel` como contrato API.
- Usar rutas legacy de payment reports como `POST /orders/:id/payment-report` como contrato API.
- Usar tabla separada de idempotencia en slice 04 sin contrato/schema completo.
- Crear `payment_evidence_files` o `storage_objects` en slice 05; la evidencia de pago usa `file_assets`.
- Devolver automaticamente una orden rechazada por negocio a `waiting_payment` sin contrato futuro de correccion/soporte/disputa.

## 2026-07-07 - Slice 14 surface separation/support intake

| Fecha | Decision | Estado |
|---|---|---|
| 2026-07-07 | NODO se separa en Mini App Cliente, Mini App Negocio, Panel Admin Web Desktop, Bot Registro Negocios y Backend unico compartido. | aprobado |
| 2026-07-07 | Mini App Cliente queda solo para remitentes/clientes y no incluye registro/verificacion de negocio, creditos de negocio, ordenes entrantes ni admin. | aprobado |
| 2026-07-07 | Mini App Negocio queda solo para `business_owner` con negocio aprobado y asociado a Telegram ID. | aprobado |
| 2026-07-07 | Panel Admin Web Desktop queda fuera de la Mini App Cliente y concentra admin, soporte, metricas, disputas, auditoria y revision de intake. | aprobado |
| 2026-07-07 | Bot Registro Negocios crea `business_intake_requests` pendientes para admin; no crea negocio activo, no publica anuncios y no promete aprobacion. | aprobado |
| 2026-07-07 | Soporte general/ticket no cambia estados de orden; chat operativo no es disputa; disputa formal sigue contratos de disputa existentes. | aprobado |
| 2026-07-07 | Documentos de intake y adjuntos de soporte usan `file_assets` con storage privado y nunca exponen `storage_path`. | aprobado |
| 2026-07-07 | Backend unico sigue siendo autoridad de auth, RBAC, datos, audit, storage, ordenes, creditos, soporte y jobs. | aprobado |
| 2026-07-07 | Mini App Negocio no pide `payment_method_id` manual; usa `GET /api/v1/business/payment-methods` para mostrar metodos propios aprobados, enmascarados y activos. B-16 queda solo lectura o placeholder gobernado en 14B; la gestion/aprobacion de metodos la controla admin. | aprobado |
| 2026-07-07 | Admin Web de 14C es Panel Web Desktop separado: usa sidebar/top bar/tablas/filtros/paginacion/split views y no usa Telegram Mini App shell, Telegram bottom nav, Telegram MainButton ni `themeParams` como reglas activas. | aprobado |
| 2026-07-07 | En Admin Web, A-01, A-02, A-03, A-06, A-07, A-08, A-09, A-10, A-11 y A-12 son ownership 14C; A-04, A-05 y A-13 siguen owned por slice 08 y solo se componen/enlazan sin cambiar reglas de creditos. | aprobado |
| 2026-07-07 | Para Mini App Negocio, Telegram ID identifica a la persona pero no autoriza por si solo. El acceso canonico usa `business_access_links` activo entre usuario/Telegram/negocio, negocio `approved`, usuario `active` y `surface = business_mini_app`. | aprobado |
| 2026-07-07 | El Bot Registro Negocios no autoriza acceso ni crea negocios activos; solo captura datos/documentos, notifica y abre la puerta. Admin Web crea/aprueba/vincula, y backend aplica la decision. | aprobado |
| 2026-07-07 | `POST /api/v1/businesses`, documentos de verificacion y `submit-verification` dejan de ser flujo activo de self-onboarding para Mini App Negocio; quedan legacy/internal o admin/bot flow hasta que un contrato futuro los retire o migre. | aprobado |
| 2026-07-07 | Suspender/bloquear negocio y suspender/bloquear acceso Telegram/persona son controles separados. `business_access_links.status` puede ser `active`, `suspended`, `revoked` o `blocked`. | aprobado |
| 2026-07-07 | Bot Registro Negocios 14D acepta solo imagen/PDF en MVP, valida contacto compartido `contact.user_id == telegram_user_id`, separa `contact_phone` de `business_phone`, procesa updates idempotentemente por `telegram_chat_id + last_update_id` y guarda documentos privados como `file_assets.resource_type = business_intake`, `file_type = intake_document`. Video queda post-MVP. | aprobado |

## 2026-07-10 - Engineering guardrails oficiales

| Fecha | Decision | Estado |
|---|---|---|
| 2026-07-10 | Se crea `00_GOVERNANCE/ENGINEERING_GUARDRAILS.md` como guardrail oficial obligatorio para arquitectura, seguridad, datos, performance, costos, concurrencia, UX, observabilidad, red team y release gates en todo NODO. | aprobado |
| 2026-07-10 | `ENGINEERING_GUARDRAILS.md` queda agregado al orden de autoridad documental justo despues de `SOURCE_OF_TRUTH.md`; un cambio que compila pero viola estos guardrails debe rechazarse hasta tener evidencia o rediseno. | aprobado |

## 2026-07-10 - Slice 19 Base USDC credit topups

| Fecha | Decision | Estado |
|---|---|---|
| 2026-07-10 | Slice 19 crea compra/acreditacion de creditos publicitarios con pagos on-chain en Base mainnet, `chain_id = 8453`. | aprobado |
| 2026-07-10 | MVP de slice 19 acepta solo USDC nativo en Base con contrato `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` y decimals `6`. | aprobado |
| 2026-07-10 | USDT Base queda fuera del MVP hasta verificacion oficial contractual; prohibido aceptar tokens por simbolo/nombre solamente. | aprobado |
| 2026-07-10 | `NODO_CREDIT_RECEIVING_WALLET_BASE` es direccion publica destino; private keys, seed phrases, mnemonics y signing keys quedan prohibidos en backend, frontend, Railway, GitHub, Cursor, logs y evidencia. Sustituido parcialmente por 52C solo para el `authorizedSigner` EIP-712 operacional; treasury/owner keys siguen prohibidas. | sustituido parcialmente |
| 2026-07-10 | Stripe/Zelle/USDT TRC20 manual quedan como fallback/legacy si backend los habilita; USDT TRC20 manual no se mezcla con Base. | aprobado |
| 2026-07-10 | Acreditacion on-chain requiere verifier backend, unique por `chain_id + tx_hash + tx_log_index`, ledger `purchase` y wallet update en transaccion exact-once. | aprobado |
| 2026-07-10 | Bot/admin privado solo notifica pagos on-chain; no decide, no acredita y no reemplaza verifier/ledger/backend. | aprobado |

## 2026-07-10 - Slice 20A Admin users and business access control

| Fecha | Decision | Estado |
|---|---|---|
| 2026-07-10 | Slice 20A contrata el primer corte del Centro de Operaciones NODO para buscar/ver usuarios, controlar estados de usuario y administrar `business_access_links` desde Admin Web. | aprobado |
| 2026-07-10 | `users.status` conserva el enum canonico existente `active`, `restricted`, `blocked`, `dormant`; la accion admin `suspend` mapea a `restricted` y no introduce enum nuevo. | aprobado |
| 2026-07-10 | Support puede ver usuarios y access links solo en modo lectura/enmascarado; `admin` y `super_admin` pueden mutar segun RBAC con reason, `Idempotency-Key` y audit. | aprobado |
| 2026-07-10 | Slice 20B separa soporte real de chat operativo y disputa formal: tickets pueden ser generales o ligados a orden/anuncio/credito, pero no cambian estados de orden, creditos, anuncios, disputas, usuarios ni access links. | aprobado |
| 2026-07-10 | Support puede responder, asignar, escalar, resolver, cerrar tickets y ver adjuntos privados con signed URL corta segun RBAC; no puede ejecutar acciones criticas de dominio desde soporte. | aprobado |
| 2026-07-10 | Admin no puede bloquear/suspender/reactivar usuarios admin/super_admin salvo permiso super_admin; nadie puede bloquear el ultimo super_admin activo. | aprobado |
| 2026-07-11 | Slice 20C contrata delegacion interna con `staff_profiles`, `staff_permissions` y `staff_invites`; `users.role` sigue como rol base y no se usa solo para granularidad staff. | aprobado |
| 2026-07-11 | Roles internos staff activos: `support_agent`, `support_lead`, `operations_readonly`, `admin` y `super_admin`; staff delegado queda limitado a soporte/lecturas enmascaradas segun permisos y scopes. | aprobado |
| 2026-07-11 | Staff delegado no puede bloquear/suspender usuarios, cambiar roles, mutar `business_access_links`, aprobar/rechazar negocios o creditos, ajustar creditos, resolver disputas ni mutar ordenes/anuncios/creditos. | aprobado |
## 2026-07-11 - slice_24_observability_debuggability contracts

Decision:

- NODO observability queda contratada como diagnostico operacional seguro, no como audit formal ni ledger financiero.
- MVP permitido: `local_only_ring_buffer + backend_persisted_events`, deshabilitado por defecto y habilitable por env solo local/staging inicialmente.
- No se autoriza proveedor externo SaaS de observability en este slice.
- Se crea modelo canonico de correlacion con `request_id`, `correlation_id`, `operation_id`, `session_id`, `surface`, version/build y referencias redaccionadas.
- Session replay sera estructurado sin video, sin DOM completo y sin payloads privados.
- Observability persistida tendra TTL, limites de costo, rate limit y masking por rol.

Estado:

```txt
READY_FOR_OWNER_APPROVAL_TO_BUILD_24
```

## 2026-08-09 - C0 reported-payment dispute reconciliation

| Fecha | Decision | Estado |
|---|---|---|
| 2026-08-09 | La decision Owner C0 sustituye las decisiones de 2026-07-04 que permitian al negocio crear `payment_rejected`. Desde `payment_reported`, el negocio confirma el pago o usa `Reportar problema con pago`, que debe abrir disputa con razon `payment_not_received_or_incomplete`. | aprobado |
| 2026-08-09 | `payment_rejected` permanece solo como estado legacy/historico para lectura, filtros, timeline y recuperacion administrativa; ninguna nueva accion del negocio debe crearlo. | aprobado |
| 2026-08-09 | Una orden que tuvo pago reportado y termina en `completed` o `cancelled` inicia un cooldown neutral de publicacion de 15 minutos; la cancelacion pre-report no lo inicia y las restricciones Admin dominan. | aprobado |

## 2026-08-19 - Admin unblock reconciliation

| Fecha | Decision | Estado |
|---|---|---|
| 2026-08-19 | Admin/Super Admin puede revertir explicitamente `users.status = blocked` a `active` y `businesses.verification_status = blocked` a `approved` mediante los endpoints `reactivate`, con reason, idempotencia, audit y notificacion existentes. El desbloqueo de una entidad no reactiva automaticamente la otra ni modifica `business_access_links`. | aprobado |

## 2026-08-21 - Slice 52C crypto credit backend signer

| Fecha | Decision | Estado |
|---|---|---|
| 2026-08-21 | NODO puede usar un `authorizedSigner` operacional separado para firmar autorizaciones EIP-712 de compras crypto de creditos publicitarios. El signer no es treasury, no es owner, no mueve fondos y no puede firmar payloads arbitrarios enviados por frontend/admin. | aprobado |
| 2026-08-21 | Produccion no debe custodiar la private key del signer como variable plana en Railway/env como diseno final. Staging/testnet puede usar signer temporal con wallet no oficial, fondos pequenos, rotacion antes de produccion, auditoria y alerta. | aprobado |
| 2026-08-21 | Para fondos reales, el flujo recomendado es `base_usdc_contract` con `purchase_ref` y autorizacion firmada. `base_usdc_onchain` directo a wallet queda legacy/fallback manual o staging hasta retiro gobernado y no debe auto-acreditar fondos reales sin prueba contractual de intencion. | aprobado |
