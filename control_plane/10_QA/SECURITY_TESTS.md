# SECURITY_TESTS.md

## Slice 14 - Surface separation, intake and support

- Mini App Cliente no expone vistas, acciones ni endpoints de negocio/admin.
- Mini App Negocio rechaza usuario sin negocio aprobado y Telegram ID asociado.
- Panel Admin Web no vive dentro de Mini App Cliente.
- `support` entra a Admin Web con permisos limitados por RBAC.
- Bot intake con webhook secreto invalido rechaza.
- Bot intake no crea negocio activo.
- Bot intake no publica anuncios.
- Bot intake no promete aprobacion.
- Bot intake valida que el contacto compartido cumpla `contact.user_id == telegram_user_id`.
- Bot intake guarda `contact_phone` separado de `business_phone`.
- Bot intake procesa `telegram_chat_id + update_id` de forma idempotente y no duplica solicitud, archivo, audit ni notificacion.
- Bot intake acepta solo `image/jpeg`, `image/png`, `image/webp` y `application/pdf`, maximo 5 MB.
- Bot intake rechaza video/local media post-MVP con `BOT_UPLOAD_INVALID`.
- Bot intake guarda documentos con `file_assets.resource_type = business_intake` y `file_type = intake_document`.
- Admin accept/reject intake requiere reason.
- Business intake documents usan storage privado y no exponen `storage_path`.
- Soporte general no cambia estados de orden.
- Soporte por orden no cambia estados de orden.
- Chat operativo no crea disputa automaticamente.
- Escalar soporte en 20B solo cambia el ticket a `escalated` o vincula una disputa existente autorizada como contexto; no crea disputa formal.
- Support attachments usan storage privado y no exponen `storage_path`.
- Cliente no puede ver ticket ni adjunto de otro cliente.
- Negocio no puede ver ticket ni adjunto de otro negocio, otra orden, otro anuncio o otra compra de creditos.
- `support` puede responder/asignar/escalar/resolver/cerrar tickets segun RBAC, pero no puede resolver disputa formal ni cambiar orden/credito/anuncio/usuario/access link desde soporte.
- Admin/support signed URL de adjunto de soporte es corta, auditada y no persistida.
- Listas admin de soporte soportan filtros status/scope/category/priority/assignee sin exponer cuerpos completos.
- Support audit metadata no guarda cuerpo completo de mensaje, `storage_path`, signed URL, datos bancarios completos, tokens ni secretos.
- Soporte debe tener rate limit en create/message/upload/assign/escalate/resolve/close/view-url.
- CORS/origenes separados para client mini app, business mini app y admin web.
- No aparecen claims prohibidos: escrow, fondos garantizados, pago garantizado, garantia de entrega.

Contrato minimo de pruebas de seguridad.

## Regla madre

Un slice sensible no pasa a `READY_FOR_OWNER_REVIEW` sin pruebas de seguridad ejecutadas o un bloqueo explicito.

## Pruebas obligatorias por superficie

### Auth Telegram

- initData valido autentica.
- hash invalido rechaza.
- initData expirado rechaza.
- usuario suspendido rechaza acciones.
- bot token no aparece en frontend bundle.

### RBAC y ownership

- remitente no ve orden ajena.
- negocio no ve orden de otro negocio.
- negocio no ajusta creditos.
- support no ejecuta acciones admin mutantes.
- admin sin permiso especifico recibe `403`.

### Creditos y pagos

- webhook Stripe sin firma valida rechaza.
- webhook Stripe repetido no acredita dos veces.
- checkout no acredita desde redirect frontend.
- pago manual requiere aprobacion admin.
- ajuste manual requiere reason y audit log.

### Ordenes y anuncios

- dos usuarios no pueden tomar el mismo anuncio.
- retry de create_order no crea duplicado si usa idempotency key.
- cancelacion antes de pago libera creditos una sola vez.
- confirmacion de pago consume creditos una sola vez.
- business list solo devuelve ordenes del negocio propio.
- business detail bloquea orden ajena sin filtrar existencia.
- confirm-payment requiere `payment_reported`, payment_report `submitted` e `Idempotency-Key`.
- confirm-payment marca payment_report `accepted`, setea delivery deadlines y no marca delivered/completed.
- confirm-payment archiva anuncio con `ad.status = archived`.
- confirm-payment idempotente no doble consume creditos.
- reject-payment-report devuelve `PAYMENT_REJECTION_NOT_ALLOWED` y no muta
  orden, reporte, credito, capacidad, anuncio, eventos ni notificaciones.
- reportar problema con pago abre una disputa atomica con razon
  `payment_not_received_or_incomplete`, mantiene el reporte `submitted`, los
  creditos bloqueados y `ad.status = in_order`.
- mark-delivered requiere `payment_confirmed`, setea delivered timers y no completa orden.
- slice 06 no construye chat, disputas ni confirmacion de recibido por remitente.

### Evidencias y datos sensibles

- evidencia privada no es publica.
- signed URL expira.
- usuario no autorizado no puede abrir comprobante.
- remitente solo puede revelar instrucciones completas de su propia orden `waiting_payment`.
- reveal de instrucciones de orden ajena no filtra existencia.
- reveal de instrucciones de orden vencida falla con error seguro.
- reveal de instrucciones setea `payment_data_revealed_at/payment_data_revealed_by` y audita `payment_instructions_viewed`.
- reportar pago no expone `account_value` ni instrucciones completas en logs/audit.
- reportar pago con Zelle exige monto bloqueado; referencia, sender name y evidencia son opcionales en el flujo simplificado.
- reportar pago con USDT TRC20 exige monto bloqueado; `tx_hash` es opcional, pero si se envia exige network TRC20 y formato canonico.
- `tx_hash` se enmascara/trunca en UI/listados/audit cuando aplique.
- logs no contienen datos bancarios completos.
- UI enmascara telefono, correo, wallet, tx_hash y referencias cuando aplique.
- documento de verificacion de negocio no es publico.
- business_owner no ve documento de otro negocio.
- support no aprueba/rechaza negocio y no obtiene documento completo por defecto.
- admin/super_admin document view requiere reason y genera `verification_document_viewed`.
- frontend/admin no expone `storage_path`.

### Rate limits

- auth/initData tiene limite.
- create_order tiene limite.
- upload evidence tiene limite.
- chat tiene limite.
- upload message attachment tiene limite.
- abrir disputa tiene limite.
- admin critical action tiene limite.

### Chat y disputas

- remitente solo ve mensajes de orden propia.
- negocio solo ve mensajes de orden de su negocio.
- usuario ajeno no puede detectar existencia de orden por chat/disputa.
- `messages` es la tabla canonica; no se crea `chat_messages`.
- crear mensaje audita `message_created`.
- crear mensaje en contexto de disputa audita `dispute_message_created`.
- adjunto de mensaje audita `message_attachment_uploaded`.
- adjunto de mensaje rechaza MIME no permitido.
- adjunto de mensaje rechaza archivo mayor a 5 MB.
- adjunto de mensaje no expone `storage_path`.
- abrir disputa desde estado permitido setea `orders.status = disputed` y guarda `previous_order_status`.
- abrir disputa desde `payment_reported/payment_rejected` mantiene creditos bloqueados y `ad.status = in_order`.
- abrir disputa desde `payment_confirmed/delivered` mantiene creditos consumidos y `ad.status = archived`.
- slice 07 no construye R-10, completion, rating, auto-complete ni admin dispute resolution.
- admin/super_admin/support pueden ver disputas solo en modo lectura segun RBAC.
- admin/super_admin/support no pueden resolver disputas en slice 07.
- no existe endpoint `POST /api/v1/admin/disputes/{id}/resolve` en slice 07.
- slice 07 no emite `dispute_resolved`; queda reservado para contrato futuro.
- slice 09 permite `POST /api/v1/admin/disputes/{id}/resolve` solo a admin/super_admin.
- support no puede resolver disputas en slice 09.
- resolve dispute exige reason e `Idempotency-Key`.
- resolve dispute misma key + mismo payload devuelve mismo resultado.
- resolve dispute misma key + payload distinto falla seguro.
- resolve dispute aplica efectos de creditos/ad.status segun `DISPUTE_RESOLUTION_MASTER.md`.
- resolve dispute crea `dispute_events` y audit `dispute_resolved`.

### Creditos, founders y referrals

- todas las rutas activas de creditos/referrals usan `/api/v1`.
- rutas legacy `/credits/balance`, `/credit-purchases` y `/credit-purchases/:id/manual-proof` no son contrato activo.
- Stripe redirect frontend no acredita creditos.
- Stripe webhook sin firma valida falla con `STRIPE_SIGNATURE_INVALID`.
- Stripe webhook duplicado no acredita dos veces.
- compra manual queda `pending_manual_review`.
- admin approve/reject de compra manual exige reason.
- compra manual rechazada no acredita creditos.
- comprobante manual usa `file_assets.resource_type = credit_purchase` y `file_type = credit_purchase_proof`.
- comprobante manual no expone `storage_path`.
- `business_owner` solo ve wallet/ledger/referrals propios.
- support ve compras de credito en modo lectura/enmascarado y no aprueba/rechaza/ajusta.
- founder activo permite publicar sin cobrar creditos y audita `founder_free_use`.
- founder expirado requiere creditos disponibles.
- `founder_access` no se crea como tabla activa.
- referrals usan `referral_codes` y `referral_events`, no tabla `referrals`.
- self-referral falla.
- doble bonus de referral falla.
- referral cap se respeta.
- referral bonus califica con compra legacy `approved` o compra Base USDC `credited`, siempre con ledger purchase exact-once.
- compra Base USDC antes de `credited` no califica referral.
- `refund` y `adjustment` no se usan como tipos activos de `credits_ledger`.
- Base USDC purchase requires Idempotency-Key.
- Base USDC valid tx credits exactly once.
- Duplicate Base tx does not double credit.
- Wrong chain fails.
- Wrong token fails.
- Wrong destination wallet fails.
- Insufficient amount goes to `under_review` and does not auto-credit.
- Expired purchase does not auto-credit.
- Pending confirmations do not credit.
- RPC unavailable returns safe error.
- Concurrent tx submit does not duplicate ledger or wallet credits.
- Watcher batch retry does not duplicate ledger or wallet credits.
- On-chain flow never stores or exposes private keys, seed phrases, RPC keys, `storage_path` or `account_value`.
- USDT Base is not accepted in MVP.

### Mini App Negocio payment methods

- business owner ve solo metodos de pago propios aprobados.
- negocio no aprobado no ve metodos de pago.
- metodos pending/rejected/disabled/suspended/blocked no aparecen.
- otro negocio no puede ver metodos ajenos.
- response de `GET /api/v1/business/payment-methods` no incluye `account_value`.
- response de `GET /api/v1/business/payment-methods` no incluye `storage_path`.
- B-08 no permite input manual de `payment_method_id`.
- B-16 no permite crear/editar/aprobar/borrar metodos en 14B.

### Errores seguros

- no stack traces.
- no SQL crudo.
- no secretos.
- no tokens.
- errores usan `ERROR_CONTRACT.md`.

### Admin

- Admin Web no importa ni renderiza Mini App Cliente ni Mini App Negocio.
- Admin Web no usa Telegram Mini App shell, Telegram bottom nav ni Telegram MainButton como navegacion primaria.
- Admin Web usa layout desktop-first con sidebar/top bar, tablas, filtros y detalle/split view.
- Admin Web no depende de `themeParams` como fuente de tema.
- Admin Web bloquea remitter/business_owner desde la superficie admin.
- `support` puede entrar solo en modo lectura segun RBAC.
- accion critica sin reason falla.
- accion critica genera audit log.
- exportacion sensible bloqueada por defecto.
- support_readonly/support no aprueba, no rechaza, no ajusta creditos.
- admin approve/reject business solo opera sobre `verification_status = pending`.
- approve business exige reason.
- reject business exige reason.
- admin dashboard/audit/metrics no expone `storage_path`, `account_value`, instrucciones completas, tokens ni secretos.
- admin metrics usa read model calculado y no datos falsos.

### Business access control 14B1

- `GET /api/v1/surface/session` es requerido antes de entrar a Mini App Negocio.
- `business_owner` sin `business_access_links.status = active` no entra a Mini App Negocio.
- Negocio `pending`, `suspended` o `blocked` devuelve estado gobernado y no habilita mutaciones.
- Link `suspended`, `revoked` o `blocked` deniega acceso aunque el negocio exista.
- Usuario `restricted`, `blocked` o `dormant` no entra a Mini App Negocio salvo contrato futuro explicito.
- Bot intake no crea negocio activo ni link activo.
- Admin link/unlink/suspend/reactivate/block requiere reason, idempotencia y audit.
- Mini App Negocio no puede usar `POST /api/v1/businesses` como self-onboarding.
- Mini App Negocio no puede usar `/api/v1/businesses/me` como gate de acceso.
- Denegaciones por superficie auditan `surface_access_denied` cuando aplique.

### Admin users/access control 20A

- admin/super_admin puede listar usuarios con filtros y cursor pagination.
- support puede listar/ver usuarios solo masked/read-only.
- remitter/business_owner no acceden a `GET /api/v1/admin/users`.
- `GET /api/v1/admin/users/{id}` no expone tokens, session internals, refresh hashes, `storage_path`, `account_value` ni secretos.
- support no recibe Telegram ID completo.
- suspend user exige reason e `Idempotency-Key`.
- suspend user setea `users.status = restricted`; no crea `users.status = suspended`.
- reactivate user solo permite `restricted|dormant -> active`.
- block user setea `blocked` y deniega acceso a superficies.
- `blocked -> active` queda prohibido en 20A.
- admin no suspende/reactiva/bloquea usuarios admin/super_admin.
- super_admin no puede suspender/bloquear el ultimo `super_admin active`.
- mutation duplicada con misma idempotency key no duplica audit/efecto.
- misma key con payload distinto falla seguro.
- admin/support pueden listar access links por business y por user segun RBAC.
- support no crea/suspende/reactiva/revoca/bloquea access links.
- link suspended/revoked/blocked bloquea Mini App Negocio.
- audit events `user_suspended`, `user_reactivated`, `user_blocked` y access-link events se registran sin datos sensibles completos.

### Business intake conversation bot 14D2

- `BUSINESS_INTAKE_BOT_TOKEN` existe solo en backend/runtime y no aparece en frontend, logs, respuestas ni build.
- Webhook de intake rechaza secret derivado de `BOT_TOKEN`.
- Webhook cliente rechaza secret derivado de `BUSINESS_INTAKE_BOT_TOKEN`.
- `/start` en Bot Registro Negocios crea o recupera draft y no crea negocio activo.
- Bot Registro Negocios no cambia `users.role`.
- Bot Registro Negocios no crea `business_access_links`.
- Bot Registro Negocios no publica anuncios ni acredita creditos.
- Contacto compartido es obligatorio y `contact.user_id` debe coincidir con `telegram_user_id`.
- Cada paso canonico persiste el campo correspondiente y avanza `last_step`.
- Input invalido no avanza `last_step`.
- Flujo completo cambia `status = submitted`.
- Update duplicado no duplica solicitud, documento, audit ni notificacion.
- `photo`/`document` valido se descarga desde Telegram con `getFile` y se guarda en storage privado.
- Video/audio/MIME no permitido responde `BOT_UPLOAD_INVALID`.
- Archivo mayor a 5 MB falla.
- Documentos de intake no exponen `storage_path`.
- `telegram_file_id` y `telegram_file_unique_id` no se exponen como URL publica.

### Internal staff roles 20C

- Staff sin permiso no ve cola.
- Staff con scope `assigned_only` solo ve tickets asignados.
- `support_agent` puede responder ticket asignado si tiene `reply_support_ticket`.
- `support_agent` no puede bloquear usuario.
- `support_agent` no puede suspender usuario.
- `support_agent` no puede cambiar rol de usuario.
- `support_agent` no puede mutar `business_access_links`.
- `support_agent` no puede resolver disputa formal.
- `support_agent` no puede aprobar/rechazar credit purchase.
- `support_agent` no puede hacer manual credit adjustment.
- `support_lead` puede asignar tickets solo con `assign_support_ticket`.
- `operations_readonly` no puede mutar tickets ni recursos de dominio.
- Staff suspendido o revocado pierde acceso inmediatamente.
- Cambios de permisos staff requieren reason, `Idempotency-Key` y audit.
- Frontend no sustituye backend permissions.
- Staff activity y list/detail enmascaran phone, telegram_id, cuerpos completos, `storage_path`, `account_value`, tokens, secretos y signed URLs.
- No se puede suspender/revocar el ultimo `super_admin active` por efecto combinado de usuario/staff.

### Jobs y notificaciones

- `job_runs.job_type` usa `expire_and_escalate_orders`; no existe `job_name` activo.
- `job_runs.status` rechaza valores fuera de `started`, `finished`, `failed`, `skipped`, `lock_not_acquired`.
- `notification_jobs.status` rechaza valores fuera de `pending`, `sent`, `failed`, `skipped`, `cancelled`.
- `notification_jobs.dedupe_key` evita duplicar recordatorios.
- Redis lock evita doble ejecucion de `expire_and_escalate_orders`.
- fallo al obtener lock registra `job_runs.status = lock_not_acquired` sin mutar datos.
- dry-run admin de jobs no muta ordenes, anuncios, creditos, disputas ni notificaciones.
- support puede ver job runs en modo lectura si RBAC lo permite, pero no ejecuta dry-run.
- metadata de jobs/notificaciones no expone `storage_path`, `account_value`, instrucciones completas, signed URLs, tokens, secretos ni evidencia privada.
- errores de jobs usan codigos de `ERROR_CONTRACT.md` con mensaje seguro.

## Evidencia requerida

Builder debe reportar:

- comando ejecutado
- resultado
- archivos de test
- casos cubiertos
- casos no cubiertos y razon

## Bloqueo

Si una prueba requerida no existe para una superficie sensible, el estado correcto es:

```txt
BLOCKED_BY_SECURITY_GAP
```
## Observability/debuggability - slice 24

Tests contractuales requeridos:

- no secrets in logs;
- no tokens in frontend replay events;
- no Telegram initData completo;
- no `storage_path`;
- no `account_value`;
- no signed URLs;
- request logging includes `request_id`;
- correlation ID propagates;
- frontend breadcrumbs redact sensitive fields;
- session replay disabled by config;
- event ingestion rate-limited;
- admin/support access respects RBAC;
- support masking enforced;
- retention cleanup documented and testable;
- error responses safe and without stack traces.
