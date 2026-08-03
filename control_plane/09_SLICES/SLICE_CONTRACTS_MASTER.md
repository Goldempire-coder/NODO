# SLICE_CONTRACTS_MASTER.md

## slice_14_surface_separation_support_intake

Objetivo:
- Separar Mini App Cliente, Mini App Negocio, Panel Admin Web Desktop y Bot Registro Negocios.
- Mantener backend unico compartido.
- Contratar business intake y soporte/tickets.

Incluye:
- `SURFACE_ARCHITECTURE_MASTER.md`
- `BUSINESS_INTAKE_MASTER.md`
- `SUPPORT_MASTER.md`
- `SURFACE_BOUNDARIES.md`
- `BOT_ARCHITECTURE.md`
- `ADMIN_WEB_ARCHITECTURE.md`
- `BUSINESS_INTAKE_LIFECYCLE.md`
- `SUPPORT_TICKET_LIFECYCLE.md`
- `SURFACE_ACCESS_POLICY.md`
- `BOT_SECURITY.md`
- `SUPPORT_SECURITY.md`
- `BUSINESS_INTAKE_API.md`
- `SUPPORT_API.md`
- `SURFACE_SESSION_API.md`
- `BUSINESS_PAYMENT_METHODS_API.md` para selector seguro de metodos aprobados en Mini App Negocio.
- `control_plane/09_SLICES/slice_14_surface_separation_support_intake/`

No incluye:
- Deploy.
- Servicios reales nuevos.
- Cambios a reglas cerradas de creditos, ordenes, pagos, disputas o ads.
- Gestion self-service de metodos de pago por negocios en 14B.
- READY_FOR_REAL_USE.

Reglas Mini App Negocio 14B:
- B-08_CREATE_AD no pide `payment_method_id` manual; usa `GET /api/v1/business/payment-methods`.
- B-16_PAYMENT_METHODS queda solo lectura o placeholder gobernado.
- Negocios no crean, editan, aprueban, deshabilitan ni borran metodos de pago en 14B.
- Las respuestas de metodos no exponen `account_value`, `storage_path` ni datos bancarios completos.

Reglas acceso negocio 14B1:
- Telegram ID identifica persona; no autoriza por si solo.
- El acceso canonico de Mini App Negocio es `GET /api/v1/surface/session` con `X-NODO-Surface: business_mini_app`.
- Requiere user `active`, rol `business_owner`, business `approved`, `business_access_links.status = active` y Telegram initData validado contra el usuario vinculado.
- Bot Registro Negocios no autoriza acceso ni crea negocios activos.
- Admin Web crea/aprueba/vincula el acceso final.
- `POST /api/v1/businesses`, verification-documents y submit-verification quedan legacy/internal o fuera de Mini App Negocio; no son self-onboarding activo.
- Suspender/bloquear negocio y suspender/bloquear acceso Telegram/persona son controles separados.

Reglas Admin Web 14C:
- Admin Web es desktop-first y separado de Mini App Cliente/Mini App Negocio.
- A-01, A-02, A-03, A-06, A-07, A-08, A-09, A-10, A-11 y A-12 son ownership de Admin Web.
- A-04, A-05 y A-13 quedan owned por slice 08 y pueden ser enlazadas/compuestas.
- UI usa sidebar/top bar/tablas/filtros/paginacion/split view.
- Prohibido usar Telegram Mini App shell, Telegram bottom nav, Telegram MainButton o `themeParams` como reglas activas.
- Admin/super_admin mutan solo con backend RBAC, reason, idempotencia, rate limit y audit.
- Support es read-only salvo contrato explicito.
- No exponer `storage_path`, `account_value`, tokens, secretos ni evidencia privada completa.

Reglas Bot Registro Negocios 14D:
- El bot no aprueba negocios, no da acceso a Mini App Negocio, no crea anuncios y no acredita creditos.
- MVP de documentos acepta solo `image/jpeg`, `image/png`, `image/webp` y `application/pdf`; video queda post-MVP.
- El contacto compartido por Telegram se guarda como `contact_phone`, separado de `business_phone`.
- El contacto compartido debe validar `contact.user_id == telegram_user_id`; si no coincide, responder `BOT_CONTACT_REQUIRED`.
- El estado conversacional de intake usa `business_intake_requests.status = draft/submitted/accepted/rejected`, `last_step`, `last_update_id`, `telegram_user_id` y `telegram_chat_id`.
- `telegram_chat_id + last_update_id` gobierna idempotencia de updates; repetir un update no duplica solicitud, archivo, audit ni notificacion.
- Documentos de intake usan `file_assets.resource_type = business_intake`, `file_type = intake_document`, storage privado y nunca exponen `storage_path`.
- Admin Web revisa y decide; el bot solo notifica estados seguros.

Reglas Bot Registro Negocios 14D2:
- El Bot Registro Negocios es un bot Telegram separado del bot cliente.
- Token backend: `BUSINESS_INTAKE_BOT_TOKEN`.
- Endpoint canonico: `POST /api/v1/business-intake/telegram/webhook/{secret}`.
- El bot cliente con `BOT_TOKEN` no procesa intake; el bot intake no procesa flujos cliente ni abre Mini App Cliente.
- `last_step` usa la secuencia canonica: `start`, `awaiting_contact`, `awaiting_business_name`, `awaiting_responsible_name`, `awaiting_city`, `awaiting_business_phone`, `awaiting_operation`, `awaiting_banks`, `awaiting_methods`, `awaiting_min_amount`, `awaiting_max_amount`, `awaiting_schedule`, `awaiting_references`, `awaiting_documents`, `submitted`.
- Cada respuesta valida se persiste inmediatamente; la solicitud queda `draft` hasta confirmacion final y luego `submitted`.
- Documentos se reciben desde Telegram como `photo` o `document`, se descargan con `getFile`, se guardan en storage privado y se deduplican por `telegram_chat_id + update_id + file_unique_id/file_id`.
- Video/audio/media no permitida responde `BOT_UPLOAD_INVALID`.
- 14D2 no crea negocio activo, no cambia roles, no crea `business_access_links`, no publica anuncios, no acredita creditos y no da acceso a Mini App Negocio.

## slice_15_scalability_runtime_hardening

Objetivo:
- Preparar NODO para escalar lecturas calientes del marketplace y trafico concurrente sin tumbar PostgreSQL ni debilitar operaciones sensibles.

Fuente de evidencia:
- `governance/owner_reviews/performance_runtime_capacity_report_02_20260710.md`.

Incluye:
- Camino optimizado para `GET /api/v1/ads/search`.
- Auth liviana solo para lecturas no sensibles de marketplace.
- Cache L1/L2 para marketplace con invalidacion.
- Guardrails de workers, thread limit y pool por worker.
- Stress c100/c200 marketplace y flujo mixto.
- Reporte de capacidad con evidencia.

No incluye:
- Auth liviana en crear orden, instrucciones de pago, reportar pago, negocio, creditos, admin, soporte, chat o bot.
- Cambios de reglas de negocio.
- Nuevas pantallas.
- Deploy.
- READY_FOR_REAL_USE.
- Declarar 10,000 simultaneos sin prueba cloud real.

Reglas:
- Marketplace puede ser mas rapido porque no revela datos privados ni mueve dinero.
- Mutaciones y datos sensibles conservan validacion fuerte.
- Cache de marketplace debe invalidarse al crear/editar/pausar/archivar anuncio, crear orden, expirar anuncio o suspender/bloquear negocio.
- Multi-worker debe calcular `workers x pool_por_worker` contra el limite real de PostgreSQL/Supabase.
- Si el ambiente no soporta c500/c1000, el builder debe reportar `BLOCKED_BY_INFRA_CAPACITY` en vez de esconder el fallo.

## slice_19_base_usdc_usdt_credit_topups

Objetivo:
- Compra y acreditacion de creditos publicitarios con pagos on-chain en Base.

Incluye:
- Base mainnet `chain_id = 8453`.
- USDC nativo Base como unico token MVP.
- USDC Base contract: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`.
- `POST /api/v1/business/credits/base-payment`.
- `GET /api/v1/business/credits/purchases/{id}`.
- `POST /api/v1/business/credits/purchases/{id}/tx-hash`.
- Watcher `verify_base_usdc_credit_purchases`.
- Tabla `credit_purchase_onchain_payments`.
- Acreditacion exact-once con `credits_ledger.type = purchase`.

No incluye:
- USDT Base hasta verificacion oficial contractual.
- USDT TRC20 automatico.
- Acreditar por screenshot/texto libre.
- Private keys, seed phrases o backend signing.
- Refunds automaticos.
- Custodia o pagos de remesas.
- READY_FOR_REAL_USE.

Reglas:
- Stripe/Zelle/USDT TRC20 manual quedan como fallback/legacy si backend los habilita; no son flujo principal Base.
- Bot privado/admin solo notifica; no decide ni acredita.
- Verifier/ledger/backend son autoridad.
- No se acepta token por simbolo/nombre solamente.

## slice_20A_admin_users_business_control

Objetivo:
- Primer corte del Centro de Operaciones NODO para control admin de usuarios, negocios y accesos.

Incluye:
- `GET /api/v1/admin/users`.
- `GET /api/v1/admin/users/{id}`.
- `POST /api/v1/admin/users/{id}/suspend`.
- `POST /api/v1/admin/users/{id}/reactivate`.
- `POST /api/v1/admin/users/{id}/block`.
- `GET /api/v1/admin/businesses/{id}/access-links`.
- `GET /api/v1/admin/users/{id}/access-links`.
- A-10 Admin Web users/remitters/control de access links.

Reglas:
- `users.status` conserva enum canonico: `active`, `restricted`, `blocked`, `dormant`.
- La accion admin `suspend` usa `restricted`; no existe `users.status = suspended`.
- `admin` y `super_admin` mutan con reason, `Idempotency-Key`, RBAC y audit.
- `support` es read-only y masked.
- No bloquear/suspender el ultimo `super_admin active`.
- No hard delete de usuarios, negocios ni access links.
- No tocar ordenes, pagos, creditos, disputas, Base USDC, bots, soporte/tickets ni deploy.

Contrato maestro para construir NODO por slices sin improvisar. Si una carpeta de slice contradice este documento, el builder debe reportar `BLOCKED_BY_CONTRACT_CONFLICT`.

## Reglas globales

- Cada slice debe ser pequeno, verificable y reversible.
- Cada slice debe entregar migraciones, API, UI, permisos, tests y audit logs solo si aplican a su scope.
- Ningun slice puede cambiar enums globales sin actualizar 04_DATA/ENUMS_AND_STATUS_MASTER.md.
- Ningun slice puede crear estados temporales no aprobados.
- Ningun slice puede prometer escrow, fondos garantizados o entrega garantizada.
- Todo slice que toque dinero, creditos, pagos o admin debe usar idempotencia y audit log.

## slice_00_foundation

Objetivo: crear base tecnica profesional.

Incluye:

- monorepo o repos separados segun decision del owner
- Next.js + TypeScript + Tailwind
- FastAPI
- estructura modular backend
- Postgres/Supabase
- Redis
- migraciones base
- lint/test/build
- manejo de envs
- health checks
- logging base

No incluye:

- UI final de negocio/remitente
- pagos reales
- ordenes reales
- admin funcional completo

QA minimo:

- build frontend
- tests backend base
- migration up/down
- health API
- Redis connectivity

## slice_01_auth_telegram

Objetivo: autenticar usuarios desde Telegram Mini App.

Tablas:

- users
- sessions
- audit_logs

API:

- POST /api/v1/auth/telegram
- POST /api/v1/auth/refresh
- POST /api/v1/auth/logout
- GET /api/v1/users/me

Seguridad:

- validar initData en backend
- JWT corto
- usuario suspendido bloqueado
- rate limit auth

UI:

- entry/welcome
- estado cargando sesion
- error de sesion expirada

No incluye:

- verificacion de negocio
- marketplace
- ordenes

## slice_02_business_verification

Objetivo: permitir que un negocio se registre y admin lo apruebe o rechace.

Tablas:

- businesses
- business_verification_submissions
- business_payment_methods
- file_assets
- audit_logs

API:

- POST /api/v1/businesses
- PUT /api/v1/businesses/{id}
- POST /api/v1/businesses/{id}/verification-documents
- POST /api/v1/businesses/{id}/submit-verification
- GET /api/v1/businesses/me
- GET /api/v1/admin/businesses/pending
- GET /api/v1/admin/businesses/{id}
- POST /api/v1/admin/businesses/{id}/verification-documents/{file_id}/view-url
- POST /api/v1/admin/businesses/{id}/approve
- POST /api/v1/admin/businesses/{id}/reject

Estados:

- pending
- approved
- rejected
- suspended
- blocked

Reglas:

- `draft` puede existir solo como estado UI/workflow antes de crear/enviar verificacion; no es `business.verification_status`.
- El estado de revision pendiente se expresa solo como `pending`.
- `under_review` pertenece a `business.risk_level`, no a `business.verification_status`.

UI:

- B-01 onboarding
- B-02 verification form
- B-03 pending
- A-02 pending businesses
- A-03 verification detail

No incluye:

- anuncios activos
- creditos pagos
- ordenes

## slice_03_ads_marketplace

Objetivo: negocio crea anuncios y remitente ve marketplace.

Tablas:

- ads
- credit_wallets lectura/bloqueo/liberacion/consumo
- credits_ledger
- audit_logs

API:

- GET /api/v1/ads/search
- GET /api/v1/ads/{id}
- POST /api/v1/business/ads
- GET /api/v1/business/ads
- GET /api/v1/business/ads/archived
- PUT /api/v1/business/ads/{id}
- POST /api/v1/business/ads/{id}/pause
- POST /api/v1/business/ads/{id}/archive

Estados:

- draft
- active
- in_order
- paused
- expired
- archived
- suspended

Reglas:

- `active` dura 7 dias desde `activated_at`.
- Pausar no extiende `expires_at`.
- Search excluye anuncios vencidos aunque sigan persistidos como active/paused hasta materializacion.
- Slice 03 usa expiracion pasiva/materializada; worker masivo queda para slice_10.
- `credit_wallets` se puede crear lazy/idempotente en slice 03 con balances cero si falta.

UI:

- R-02 home/search
- R-03 results
- R-04 business detail
- B-08 create ad
- B-09 my ads
- B-10 archived ads

No incluye:

- crear orden
- reporte de pago
- chat

## slice_04_order_creation

Objetivo: crear orden con snapshot inmutable del anuncio.

Tablas:

- orders
- order_state_events
- audit_logs
- ads

API:

- POST /api/v1/orders
- GET /api/v1/orders/{id}
- GET /api/v1/orders/mine
- POST /api/v1/orders/{id}/extend-payment-deadline
- POST /api/v1/orders/{id}/cancel

Estados relacionados:

- waiting_payment
- cancelled

`created` puede existir solo como audit/state event de creacion; `POST /api/v1/orders` persiste directamente `waiting_payment`.

Reglas:

- usar idempotency key
- usar `orders.idempotency_key`; no usar tabla separada de idempotencia en slice 04
- snapshot inmutable de tasa, monto, limites, negocio, metodo, delivery e instrucciones privadas
- no revelar instrucciones completas en create/detail/list; slice 05 las revela con `GET /api/v1/orders/{id}/payment-instructions`
- no modificar snapshot monetario despues de crear
- no crear orden si anuncio no esta active
- 1 anuncio solo puede tener 1 orden activa en MVP
- crear orden cambia `ad.status` a `in_order`
- crear orden no consume creditos ni cobra al usuario
- cancel en slice 04 solo aplica a `waiting_payment` antes de reporte de pago
- extend en slice 04 solo aplica una vez a `waiting_payment`
- expiracion masiva queda para slice 10; slice 04 materializa pasivamente ordenes `waiting_payment` vencidas al leer o mutar

UI:

- R-05 create order
- R-06 order summary
- R-12 my orders

No incluye:

- R-07 payment instructions salvo link/estado hacia slice 05
- B-11 incoming orders, pertenece a slice 06
- confirmar pago
- entrega
- disputa

## slice_05_payment_instructions_reports

Objetivo: mostrar instrucciones y permitir reporte de pago.

Tablas:

- payment_reports
- file_assets para payment_evidence
- order_state_events
- audit_logs

API:

- GET /api/v1/orders/{id}/payment-instructions
- POST /api/v1/orders/{id}/payment-report
- POST /api/v1/orders/{id}/payment-evidence

Estados:

- waiting_payment -> payment_reported

Reglas:

- GET payment-instructions revela instrucciones completas solo al remitente dueno.
- GET payment-instructions requiere `waiting_payment` y orden no vencida.
- GET payment-instructions setea `payment_data_revealed_at` y `payment_data_revealed_by`.
- GET payment-instructions audita `payment_instructions_viewed`.
- GET payment-instructions no crea payment report ni cambia status.
- POST payment-report requiere `Idempotency-Key`.
- POST payment-report crea `payment_reports.status = submitted`.
- POST payment-report setea `orders.status = payment_reported` y `paid_reported_at`.
- POST payment-report mantiene `ad.status = in_order`.
- POST payment-report mantiene creditos bloqueados.
- POST payment-report no consume creditos, no confirma negocio, no entrega y no completa orden.
- Zelle requiere el monto bloqueado de la orden. El comprobante es opcional y
  el negocio puede solicitarlo dentro del chat.
- USDT requiere el monto bloqueado de la orden. El cliente puede marcar enviado
  sin `tx_hash`; si el negocio necesita hash o comprobante adicional, debe
  pedirlo dentro del chat. El cliente debe confirmar por chat la red exacta
  antes de enviar fondos.
- Evidencia privada usa `file_assets`; no crear `payment_evidence_files` ni `storage_objects` en slice 05.

Seguridad:

- storage privado
- signed URLs
- validar ownership
- rate limit reveal/report/upload
- idempotencia en report/upload
- no account_value en listados/logs/audit
- no storage_path en API/frontend/logs/audit

UI:

- R-07 payment instructions
- R-08 report payment

No incluye:

- negocio confirma pago
- negocio rechaza pago
- entrega/pago movil
- chat
- admin resuelve disputa
- jobs masivos
- consumo de creditos
- R-09 tracking/chat salvo link hacia slice 07

## slice_06_business_order_ops

Objetivo: negocio opera ordenes recibidas, confirma/rechaza reporte de pago y marca pago movil enviado.

Tablas:

- orders
- payment_reports
- order_state_events
- credit_wallets
- credits_ledger
- audit_logs

API:

- GET /api/v1/business/orders
- GET /api/v1/business/orders/{id}
- POST /api/v1/business/orders/{id}/confirm-payment
- POST /api/v1/business/orders/{id}/reject-payment-report
- POST /api/v1/business/orders/{id}/mark-delivered

Estados:

- payment_reported -> payment_confirmed
- payment_reported -> payment_rejected si se rechaza reporte
- payment_confirmed -> delivered

Reglas:

- contrato API canonico: `06_API_CONTRACTS/BUSINESS_ORDERS_API.md`
- todo endpoint requiere auth JWT y actor `business_owner` activo
- solo ordenes del negocio propio
- no filtrar existencia de ordenes ajenas
- mutaciones requieren `Idempotency-Key`
- confirmar pago requiere `payment_reported` y payment_report `submitted`
- confirmar pago setea `payment_confirmed_at`, delivery deadlines y `payment_reports.status = accepted`
- confirmar pago consume creditos bloqueados exactamente una vez mediante ledger `consume`
- confirmar pago setea `ad.status = archived`; la orden sigue viva, pero el anuncio ya cumplio su funcion y no vuelve al marketplace
- rechazar reporte requiere reason, setea `orders.status = payment_rejected` y `payment_reports.status = rejected`
- rechazar reporte no consume creditos, no libera anuncio, no libera creditos y mantiene `ad.status = in_order`
- marcar entregado requiere `payment_confirmed`, setea `delivered_at` y timers de auto-complete
- marcar entregado no completa la orden

UI:

- B-11 incoming orders
- B-12 business order detail

No incluye:

- disputa admin
- chat
- B-13 business chat salvo link/estado hacia slice 07
- R-09 tracking/chat
- R-10 confirm received
- auto-complete
- jobs masivos
- compra/acreditacion real de creditos

## slice_07_chat_disputes

Objetivo: chat por orden, adjuntos privados y apertura de disputas.

Tablas:

- messages
- message_attachments
- disputes
- dispute_events
- audit_logs

API:

- GET /api/v1/orders/{id}/messages
- POST /api/v1/orders/{id}/messages
- POST /api/v1/orders/{id}/message-attachments
- POST /api/v1/orders/{id}/disputes
- GET /api/v1/admin/disputes
- GET /api/v1/admin/disputes/{id}

UI:

- R-09 tracking/chat
- B-13 business chat

No incluye:

- cambiar pagos sin state machine
- prometer proteccion de fondos
- R-10 confirm received
- R-11 rating
- A-06 disputes list
- A-07 dispute detail
- completar orden
- confirmar recepcion del remitente
- auto-complete
- resolver disputas admin
- mover creditos por resolucion de disputa
- cambiar `ad.status` por resolucion de disputa

Reglas:

- La tabla canonica de mensajes es `messages`; `chat_messages` queda como nombre legacy/no valido.
- Abrir disputa mueve la orden a `disputed` y guarda `previous_order_status` en `disputes`.
- Disputas desde `payment_reported` o `payment_rejected` mantienen creditos bloqueados y `ad.status = in_order`.
- Disputas desde `payment_confirmed` o `delivered` mantienen creditos ya consumidos y `ad.status = archived`.
- R-10, completion, rating y auto-complete quedan para slice futuro.

## slice_08_credits_referrals

Objetivo: creditos publicitarios, Stripe, Zelle/USDT manual, fundador y referidos.

Tablas:

- credit_wallets
- credits_ledger
- credit_purchases
- businesses founder fields (`founder_status`, `founder_started_at`, `founder_expires_at`)
- referral_codes
- referral_events
- file_assets para comprobantes privados de compras manuales
- audit_logs

Legacy/no valido:

- `founder_access` como tabla activa MVP.
- `referrals` como tabla activa nueva.

API:

- GET /api/v1/business/credits/wallet
- GET /api/v1/business/credits/ledger
- POST /api/v1/business/credits/stripe-checkout
- POST /api/v1/webhooks/stripe
- POST /api/v1/business/credits/manual-payment
- GET /api/v1/business/referrals
- POST /api/v1/business/referrals/apply
- GET /api/v1/admin/credit-purchases
- POST /api/v1/admin/credit-purchases/{id}/approve
- POST /api/v1/admin/credit-purchases/{id}/reject
- POST /api/v1/admin/credits/adjust

Reglas:

- Stripe acredita solo con webhook verificado e idempotente.
- Redirect frontend de Stripe nunca acredita creditos.
- Zelle/USDT manual queda pendiente hasta aprobacion admin.
- Comprobantes manuales usan `file_assets.resource_type = credit_purchase`, `file_type = credit_purchase_proof`, storage privado y nunca exponen `storage_path`.
- Founder access dura 30 dias con limites de riesgo y usa campos en `businesses`.
- Referidos usan `referral_codes` + `referral_events`; no tabla `referrals`.
- `refund` y `adjustment` no son tipos activos de `credits_ledger`; usar `release` y `admin_adjustment`.
- Creditos son publicitarios/listing: se bloquean al publicar un anuncio por 7 dias segun rango.
- Los creditos se consumen cuando el negocio confirma que recibio el pago.
- Los creditos se liberan si la orden expira o se cancela antes de pago confirmado.
- Clicks y ordenes abandonadas no consumen creditos adicionales.
- Crear orden solo hace hold temporal de disponibilidad; release si no avanza.
- Esto no es spread ni comision monetaria sobre el monto cambiado.
- Ledger append-only.

UI:

- B-04_BUSINESS_DASHBOARD
- B-05_BUY_CREDITS
- B-06_CREDIT_PAYMENT_PENDING
- B-07_MY_CREDITS_LEDGER
- B-15_REFERRAL_PROGRAM
- A-04_PENDING_CREDIT_PAYMENTS
- A-05_CREDIT_PAYMENT_DETAIL
- A-13_MANUAL_ADJUSTMENTS

Nombres legacy/no canonicos:

- `B-04_CREDITS_DASHBOARD` -> `B-04_BUSINESS_DASHBOARD`
- `B-06_PAYMENT_PROOF` -> `B-06_CREDIT_PAYMENT_PENDING`
- `B-07_REFERRALS` -> `B-15_REFERRAL_PROGRAM`
- `A-04_CREDIT_PAYMENTS` -> `A-04_PENDING_CREDIT_PAYMENTS`

No incluye:

- auto-aprobar comprobantes manuales
- guardar fondos de usuarios

## slice_09_admin_console

Objetivo: panel admin funcional completo y gobernado.

Incluye:

- dashboard
- negocios pendientes
- verificacion detalle
- pagos manuales de creditos como composicion/enlace de slice 08
- disputas admin con vista y resolucion contratada
- reportes de evasion/riesgo
- usuarios/remitentes
- metricas como read model calculado desde tablas existentes
- audit logs
- ajustes manuales con reason como composicion/enlace de slice 08

Resolucion admin de disputas:

- endpoint canonico `POST /api/v1/admin/disputes/{id}/resolve`
- admin/super_admin pueden resolver
- support es read-only
- requiere `Idempotency-Key`
- requiere reason
- usa `resolution_type` canonico de `ENUMS_AND_STATUS_MASTER.md`
- efectos de orden, creditos, ledger y anuncio definidos por `DISPUTE_RESOLUTION_MASTER.md`
- NODO registra decision operativa; no recibe, retiene, transfiere ni garantiza fondos

API:

- GET /api/v1/admin/dashboard
- GET /api/v1/admin/businesses
- GET /api/v1/admin/businesses/{id}
- GET /api/v1/admin/orders
- GET /api/v1/admin/orders/{id}
- GET /api/v1/admin/disputes
- GET /api/v1/admin/disputes/{id}
- POST /api/v1/admin/disputes/{id}/resolve
- GET /api/v1/admin/audit-logs
- GET /api/v1/admin/metrics
- endpoints de creditos/admin previos quedan definidos por `CREDITS_API.md`

Seguridad:

- RBAC admin
- super_admin para roles
- audit obligatorio
- reason obligatorio en acciones sensibles
- idempotencia obligatoria en mutaciones
- support read-only
- no export sensible salvo contrato explicito y seguro

UI:

- Owned by slice 09: A-01, A-02, A-03, A-06, A-07, A-08, A-09, A-10, A-11, A-12.
- Linked/composed from slice 08, not re-owned: A-04, A-05, A-13.

No incluye:

- operar sin roles
- permitir acciones admin desde frontend sin backend policy
- reconstruir pantallas o logica de creditos de slice 08
- slice 10 jobs, auto-complete, ratings o deploy
- escrow, fondos garantizados o procesamiento real de remesas

## slice_10_jobs_notifications

Objetivo: workers y notificaciones.

Incluye:

- expiracion de ordenes
- job `expire_and_escalate_orders`
- recordatorios de pago
- recordatorios de negocio
- expiracion founder access
- expiracion anuncios
- procesamiento async de webhooks
- notificaciones Telegram
- admin/ops job run read endpoints y dry-run protegido

Timers obligatorios:

- `waiting_payment`: 30 min + extension unica de 15 min; si vence, cancelled/payment_not_reported_in_time, anuncio activo, creditos liberados.
- `payment_reported`: 2h warning al negocio; 6h disputa/business_no_payment_confirmation, ad.status = in_order, creditos siguen bloqueados.
- `payment_confirmed`: 30 min warning; 2h disputa/business_confirmed_payment_but_not_delivered, ad.status = archived, creditos ya consumidos.
- `delivered`: recordatorios al momento, 12h y 23h; 24h auto completed con completion_reason auto_completed_after_24h si no hay disputa.

Reglas:

- jobs idempotentes
- `job_runs.job_type` es canonico; `job_name` esta prohibido/no valido
- locks Redis con TTL
- retries con backoff
- dead letter o registro de fallos
- no liberar creditos si el cliente reporto pago y el negocio no respondio; pasar a disputa
- no cancelar automaticamente una orden con pago reportado
- `notification_jobs.notification_type` y `dedupe_key` son canonicos para evitar duplicados
- `job_runs.status`: started, finished, failed, skipped, lock_not_acquired
- `notification_jobs.status`: pending, sent, failed, skipped, cancelled
- `R-10_CONFIRM_RECEIVED` no se construye en slice 10; este slice solo hace auto-complete por timer

No incluye:

- cambiar estados sin state machine
- confirmacion manual del remitente
- resolucion admin de disputas
- deploy, servicios reales o credenciales reales
- pagos reales, escrow o garantias de fondos
- enviar spam

## slice_11_hardening_deploy

Objetivo: preparar deploy productivo y prueba real controlada.

Incluye:

- hardening auth/RBAC
- headers seguridad
- rate limits
- backups
- restore test
- monitoreo
- alertas
- carga/concurrencia
- runbooks
- rollback
- smoke tests

No incluye:

- declarar READY_FOR_REAL_USE
- cambiar scope funcional sin owner

Gate:

- solo puede terminar en BLOCKED o READY_FOR_OWNER_REVIEW.

## slice_20B_support_ticket_center

Objetivo: construir un centro de soporte real separado por superficies.

Incluye:

- soporte cliente general `client_general`
- soporte cliente por orden `client_order`
- soporte negocio general `business_general`
- soporte negocio por orden `business_order`
- soporte negocio por anuncio `business_ad`
- soporte negocio por compra/credito `business_credit`
- cola Admin Web de soporte con filtros, detalle, mensajes, asignacion, escalamiento, resolucion, cierre, eventos y adjuntos
- `support_tickets`, `support_messages`, `support_ticket_events`
- adjuntos privados via `file_assets` con `resource_type = support_ticket|support_message` y `file_type = support_attachment`
- endpoints `/api/v1/support/tickets` y `/api/v1/admin/support/tickets`
- RBAC de `support`, `admin` y `super_admin` para operar tickets segun contrato

Reglas:

- soporte no es chat operativo entre partes
- soporte no es disputa formal
- escalar soporte no crea disputa formal en 20B
- soporte no cambia estados de orden, creditos, anuncios, usuarios, roles, access links ni disputa formal
- todos los adjuntos usan storage privado, signed URL corta y audit
- audit no guarda cuerpos completos, `storage_path`, signed URLs, tokens, secretos ni datos bancarios completos

No incluye:

- resolver disputas formales
- crear disputas desde soporte
- modificar dinero/creditos
- cambiar lifecycle de ordenes/anuncios/pagos/disputas
- soporte por voz, SLA avanzado, macros, exportaciones sensibles o automatizacion IA
- Admin Web nuevo fuera de la composicion de soporte contratada
- deploy o READY_FOR_REAL_USE

## slice_20C_internal_staff_roles

Objetivo:
- Delegacion interna segura para empleados/colaboradores sin entregar permisos peligrosos.

Incluye:
- `staff_profiles`, `staff_permissions`, `staff_invites`.
- Roles internos staff: `support_agent`, `support_lead`, `operations_readonly`, `admin`, `super_admin`.
- Permisos granulares para soporte, adjuntos y lecturas enmascaradas.
- Endpoints `/api/v1/admin/staff`.
- Staff Center, Staff Detail e Invite Staff en Admin Web.
- Audit events `staff_*`.

Reglas:
- `users.role` sigue siendo rol base y no se usa solo para granularidad staff.
- Staff activo requiere `users.status = active` y `staff_profiles.status = active`.
- Solo `super_admin` administra staff/permisos.
- Staff delegado opera solo permisos/scopes activos.
- Revocar/suspender staff corta capacidades inmediatamente pero no bloquea necesariamente al usuario.
- Staff delegado no puede bloquear/suspender usuarios, cambiar roles, mutar `business_access_links`, aprobar/rechazar negocios o creditos, ajustar creditos, resolver disputas, mutar ordenes, mutar anuncios ni mutar creditos.

No incluye:
- SSO corporativo.
- Exportaciones sensibles.
- Staff en Mini Apps.
- Cambios a soporte 20B, ordenes, creditos, anuncios, pagos o disputas.
- Deploy o READY_FOR_REAL_USE.

## slice_24_observability_debuggability

Objetivo:
- Observabilidad y depurabilidad segura para reconstruir incidentes sin capturar datos sensibles innecesarios.

Incluye:
- modelo canonico de `request_id`, `correlation_id`, `operation_id` y `session_id`;
- request logging estructurado backend;
- breadcrumbs frontend seguros;
- session replay estructurado sin video;
- ingestion backend env-gated de eventos redaccionados;
- tabla futura `observability_events` con TTL;
- Admin Web diagnostic search/export con RBAC y masking;
- cleanup de retencion;
- redaccion obligatoria y limites de costo.

Reglas:
- Observability no autoriza acciones.
- Observability no es audit formal.
- Observability no es ledger financiero.
- Audit formal sigue siendo durable para acciones sensibles.
- Session replay no graba video, DOM completo ni payloads privados.
- Produccion queda deshabilitada por defecto hasta aprobacion owner posterior.

No incluye:
- proveedores externos SaaS;
- video replay;
- cambios de reglas de negocio;
- deploy;
- READY_FOR_REAL_USE.
