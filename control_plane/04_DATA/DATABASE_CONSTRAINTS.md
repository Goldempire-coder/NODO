# DATABASE_CONSTRAINTS.md

Estas constraints son obligatorias. Si una migracion no puede aplicarlas, el builder debe detenerse y reportar `BLOCKED_BY_MISSING_CONSTRAINT`.

## Reglas generales

- Todas las tablas principales mutables deben tener `id uuid primary key`, `created_at timestamptz not null`, `updated_at timestamptz not null`.
- Tablas append-only como `audit_logs` y ledger pueden omitir `updated_at` si la policy prohibe update.
- Toda tabla con actor debe guardar `created_by_user_id` o equivalente.
- Toda transicion sensible debe generar audit log inmutable.
- Prohibido hard delete en usuarios, negocios, anuncios, ordenes, pagos, disputas, mensajes, creditos y audit logs. Usar `deleted_at` solo donde aplique.
- Montos monetarios: usar integer cents para USD o decimal con precision definida. Prohibido float.
- Tasa Bs/USD: decimal con precision definida. Prohibido float.
- Campos JSONB solo para metadata no critica; lo critico debe estar en columnas tipadas.

## Usuarios

- `users.telegram_id` unique when not null en `slice_00_foundation`; desde `slice_01_auth_telegram`, usuario autenticado debe tener `telegram_id` not null.
- `users.status` CHECK contra enum oficial.
- `users.role` CHECK contra roles oficiales.
- `users.phone` nullable, no unique global salvo que se active verificacion futura.
- Un usuario puede tener perfil remitente y negocio, pero los permisos se derivan por rol y ownership.
- En 20A, suspender usuario usa `users.status = restricted`; no se agrega `suspended` a `users.status`.
- `blocked` no borra ni trunca datos asociados; la denegacion ocurre en auth/surface policies.
- Mutaciones admin de `users.status` requieren audit/idempotency/reason a nivel servicio.

## Sesiones

- `sessions.user_id` FK users(id).
- `sessions.refresh_token_hash` unique not null.
- `sessions.status` CHECK contra enum oficial.
- `sessions.expires_at` not null.
- `sessions.refresh_token_hash` guarda hash, nunca token plano.
- `sessions.revoked_at` solo existe cuando status = `revoked`.
- Refresh debe rotar `refresh_token_hash`.
- Logout debe marcar sesion como `revoked`; no hard delete.
- Usuarios `blocked` no pueden refrescar sesion ni operar.

## Negocios

- `businesses.owner_user_id` FK users(id).
- `businesses.verification_status` CHECK contra enum oficial.
- `businesses.trust_level` CHECK contra enum oficial de capacidad interna.
- `businesses.reputation_tier` CHECK IN (`new`, `active`, `reliable`, `elite`).
- `businesses.risk_level` CHECK contra enum oficial.
- `businesses.approved_at` solo puede existir si `verification_status` es `approved`.
- `businesses.business_name` not null despues de enviar verificacion.
- `businesses.country` default `VE` para operacion inicial de entrega.
- `businesses.min_order_amount_usd >= 0`.
- `businesses.max_order_amount_usd >= businesses.min_order_amount_usd`.
- `businesses.daily_limit_usd >= 0`.
- `businesses.active_order_limit >= 0`.
- Contadores de reputacion en `businesses` son no negativos.
- `businesses.rating_avg` es null o esta entre 1.00 y 5.00.
- `businesses.success_rate` es null o esta entre 0.00 y 100.00.
- `businesses.average_delivery_seconds` es null o no negativo.
- No puede existir mas de un negocio activo con el mismo owner y mismo nombre normalizado sin revision admin.

## Ratings

- `ratings.order_id` FK `orders(id)` y unique: maximo un rating por orden.
- `ratings.business_id` FK `businesses(id)`.
- `ratings.rater_user_id` FK `users(id)`.
- `ratings.stars` CHECK entre 1 y 5.
- No existen columnas de comentario, titulo o resena textual en MVP.
- Ownership y estado `completed` se validan transaccionalmente en el servicio
  futuro antes de insertar.

## Vinculo de acceso negocio

- `business_access_links.id` uuid primary key.
- `business_access_links.business_id` FK businesses(id).
- `business_access_links.user_id` FK users(id).
- `business_access_links.telegram_id_snapshot` bigint not null.
- `business_access_links.role_in_business` CHECK IN (`owner`, `operator`).
- `business_access_links.status` CHECK IN (`active`, `suspended`, `revoked`, `blocked`).
- `business_access_links.linked_by_admin_id` FK users(id) not null.
- `business_access_links.linked_at` timestamptz not null.
- `business_access_links.reason` obligatorio cuando `status in ('suspended', 'revoked', 'blocked')`.
- `business_access_links.suspended_at` obligatorio cuando `status = 'suspended'`.
- `business_access_links.blocked_at` obligatorio cuando `status = 'blocked'`.
- `business_access_links.revoked_at` obligatorio cuando `status = 'revoked'`.
- Solo puede existir un link `active` por `(business_id, user_id, role_in_business)` en MVP.
- Solo puede existir un owner activo por negocio en MVP.
- Para acceder a `business_mini_app`, `users.telegram_id` debe coincidir con `telegram_id_snapshot` del link activo y con el Telegram initData validado.
- 20A no hard-deletea `business_access_links`; revoke/block/suspend son cambios de estado auditados.

## Verificacion de negocios

- `business_verification_submissions.business_id` FK businesses(id).
- `business_verification_submissions.submitted_by_user_id` FK users(id).
- `business_verification_submissions.admin_reviewed_by_user_id` FK users(id) nullable.
- `business_verification_submissions.status` CHECK IN (`pending`, `approved`, `rejected`).
- `business_verification_submissions.submitted_data_json` JSONB not null, solo para snapshot de datos enviados; no reemplaza columnas tipadas criticas de `businesses`.
- `business_verification_submissions.submitted_at` not null.
- `business_verification_submissions.admin_reason` obligatorio cuando `status = rejected`.
- `business_verification_submissions.reviewed_at` obligatorio cuando `status in ('approved', 'rejected')`.
- Solo puede existir una submission `pending` por negocio.
- Cada submission debe tener trazabilidad por `audit_logs` con `resource_type = 'business'` o `resource_type = 'business_verification_submission'`.
- No guardar documentos, storage keys privados, tokens ni datos bancarios completos en audit logs.
- Datos sensibles de submission/documentos se muestran enmascarados salvo permiso admin explicito.

## File assets

- Los documentos de verificacion y evidencias privadas viven en `file_assets` y storage privado.
- `file_assets.owner_user_id` FK users(id).
- Para verificacion de negocio, `file_assets.resource_type = business`.
- Para evidencia de pago, `file_assets.resource_type = payment_report`.
- Para adjuntos de mensajes, `file_assets.resource_type = message`.
- Para comprobantes manuales de compra de creditos, `file_assets.resource_type = credit_purchase`.
- Para verificacion de negocio, `file_assets.resource_id` debe referenciar el `businesses.id` asociado.
- Para evidencia de pago, `file_assets.resource_id` debe referenciar `payment_reports.id`.
- Para adjuntos de mensajes, `file_assets.resource_id` debe referenciar `messages.id` cuando el adjunto quede asociado al mensaje final.
- Para comprobantes manuales de creditos, `file_assets.resource_id` debe referenciar `credit_purchases.id`.
- `file_assets.file_type` CHECK IN (`rif_document`, `business_license`, `owner_identity`, `address_proof`, `payment_evidence`, `message_attachment`, `credit_purchase_proof`, `intake_document`).
- `file_assets.storage_path` not null y nunca se expone en API publica/frontend.
- `file_assets.mime_type` permitido para documentos/evidencia: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`.
- `file_assets.size_bytes <= 5242880` para documentos de verificacion y evidencia de pago.
- Acceso a documentos completos solo por signed URL corta y audit event cuando admin abre el documento.

## Metodos de pago/entrega

- `payment_method` CHECK IN (`zelle`, `usdt_trc20`).
- `delivery_method` CHECK IN (`pago_movil_ve`).
- Cada metodo activo debe pertenecer a un negocio aprobado.
- Un metodo marcado como visible debe tener instrucciones completas.
- Cambios de instrucciones deben versionarse o auditarse.
- Selectores de Mini App Negocio solo pueden leer metodos `approved` y `active` del negocio propio.
- `account_value` completo no se expone en selectores, frontend, logs ni audit metadata.

## Anuncios

- `ads.business_id` FK businesses(id).
- `ads.payment_method_id` FK business_payment_methods(id).
- `ads.status` CHECK contra enum oficial.
- `ads.payment_method` CHECK IN (`zelle`, `usdt_trc20`).
- `ads.delivery_method` CHECK IN (`pago_movil_ve`).
- `ads.amount_min_usd >= businesses.min_order_amount_usd` por validacion de servicio.
- `ads.amount_max_usd >= ads.amount_min_usd`.
- `ads.amount_max_usd <= 2000` para MVP salvo contrato futuro de revision manual.
- `ads.amount_max_usd <= businesses.max_order_amount_usd` salvo override admin auditado.
- `ads.rate_bs_per_usd > 0`.
- `ads.required_credits` se calcula por `amount_max_usd` y debe ser 1, 2 o 3 en MVP.
- `ads.activated_at` y `ads.expires_at` son obligatorios cuando `status in ('active', 'paused', 'in_order')`.
- `ads.expires_at = ads.activated_at + interval '7 days'` al publicar.
- Unique parcial: un negocio no puede tener dos anuncios `active` con misma combinacion `payment_method`, `delivery_method` y rango solapado.
- Un anuncio no puede activarse si el negocio no esta `approved`.
- Un anuncio no puede activarse si el negocio no tiene creditos publicitarios o founder access vigente.
- Pausar anuncio no modifica `expires_at`.
- Marketplace no muestra anuncios vencidos aunque el estado persistido aun sea `active` o `paused`.
- Slice 03 materializa expiracion pasiva al leer/mutar anuncios vencidos; worker masivo queda para `slice_10_jobs_notifications`.

## Ordenes

- `orders.remitter_user_id` FK users(id).
- `orders.business_id` FK businesses(id).
- `orders.ad_id` FK ads(id).
- `orders.status` CHECK contra enum oficial.
- `orders.public_order_code` unique not null.
- `orders.idempotency_key` nullable; si existe debe participar en indice unico parcial con `remitter_user_id`.
- `orders.cancel_reason` CHECK contra enum oficial cuando status = `cancelled`.
- `orders.dispute_reason` CHECK contra enum oficial cuando status = `disputed`.
- `orders.amount_usd >= 20`.
- `orders.rate_snapshot > 0`.
- `orders.amount_bs_calculated > 0`.
- `orders.payment_method_snapshot` y `delivery_method_snapshot` son obligatorios.
- La orden debe guardar snapshot inmutable de nombre del negocio, tasa, monto, instrucciones privadas, metodo, delivery y limites usados al crearla.
- `orders.payment_instructions_snapshot` es privado y no se expone completo en create/detail/list de slice 04.
- Idempotencia: unique parcial por `idempotency_key`, `remitter_user_id` y ventana de creacion.
- Una orden solo puede cambiar de estado por state machine oficial.
- Prohibido modificar snapshots monetarios despues de crear la orden.
- `waiting_payment` debe tener deadline de reporte de pago.
- Extension de pago solo puede usarse una vez.
- `payment_reported` debe tener deadline de respuesta de negocio.
- `payment_confirmed` debe tener deadline de entrega.
- `delivered` debe tener deadline de auto-completado a 24h.
- `payment_rejected` no debe tener `completion_reason`; mantiene trazabilidad para correccion/soporte/disputa futura.
- `payment_rejected` no libera automaticamente anuncio ni creditos.
- Confirmar pago debe setear `payment_confirmed_at`, `delivery_warning_at` y `delivery_deadline_at`.
- Marcar entregado debe setear `delivered_at`, `auto_complete_warning_12h_at`, `auto_complete_warning_23h_at` y `auto_complete_at`.

## Reportes de pago

- `payment_reports.order_id` FK orders(id).
- `payment_reports.reported_by_user_id` FK users(id).
- Solo una evidencia activa por intento; si se corrige, crear nueva version y auditar.
- `payment_reports.status` CHECK contra enum oficial.
- `payment_reports.payment_type` CHECK IN (`zelle`, `usdt_trc20`).
- `payment_reports.payment_amount > 0`.
- Para Zelle: `payment_reference`, `payment_sender_name` y `proof_file_id` son obligatorios.
- Para USDT TRC20: `tx_hash` es obligatorio y `network = TRC20`.
- Unique parcial: un `payment_reports.status = submitted` activo por `order_id`.
- Unique parcial: `(reported_by_user_id, idempotency_key)` cuando `idempotency_key is not null`.
- Debe existir `reported_by_user_id`, timestamp y metadata de archivo/comprobante cuando aplique.
- No se permite confirmar pago si la orden no esta en estado compatible.
- `proof_file_id` debe pertenecer al mismo order/payment_report y owner; servicio debe validarlo.
- Confirmacion del negocio requiere `payment_reports.status = submitted` y cambia el reporte a `accepted`.
- Rechazo del negocio requiere `payment_reports.status = submitted` y cambia el reporte a `rejected`.

## Chat y disputas

- `messages.order_id` FK orders(id).
- `messages.sender_user_id` FK users(id).
- `messages.sender_role` CHECK contra enum oficial.
- `messages.visibility` CHECK contra enum oficial.
- `messages.status` CHECK contra enum oficial.
- `messages.body` max 2000 caracteres; servicio debe exigir body o al menos un adjunto.
- `messages.deleted_at` se usa para baja logica; no hard delete.
- `messages.idempotency_key` participa en unique parcial con `sender_user_id` cuando no sea null.
- Mensajes solo entre remitente, negocio, admin/super_admin y support autorizado segun RBAC.
- `chat_messages` es nombre legacy/no valido para nuevas migraciones.
- `message_attachments.message_id` FK messages(id) nullable durante pending upload.
- `message_attachments.order_id` FK orders(id).
- `message_attachments.file_asset_id` FK file_assets(id).
- `message_attachments.uploaded_by_user_id` FK users(id).
- `message_attachments.file_type = message_attachment`.
- `message_attachments.mime_type` CHECK IN (`image/jpeg`, `image/png`, `image/webp`, `application/pdf`).
- `message_attachments.size_bytes <= 5242880`.
- `message_attachments.status` CHECK contra enum oficial.
- Adjuntos deben usar storage privado; `storage_path` vive solo en `file_assets` y no se expone.
- `disputes.order_id` FK orders(id).
- `disputes.opened_by_user_id` FK users(id).
- `disputes.previous_order_status` CHECK IN (`payment_reported`, `payment_rejected`, `payment_confirmed`, `delivered`).
- `disputes.reason` CHECK contra enum oficial de `order.dispute_reason`.
- `disputes.status` CHECK contra enum oficial.
- `disputes.order_id` unique parcial mientras `status in ('open', 'in_review')`.
- `dispute_events.dispute_id` FK disputes(id).
- `dispute_events.order_id` FK orders(id).
- `dispute_events.actor_user_id` FK users(id).
- `dispute_events` append-only.
- Slice 09 admin resolution requires `disputes.resolution_reason` when `status in ('resolved', 'cancelled')`.
- Slice 09 admin resolution requires `disputes.resolved_by_admin_id` when `status = 'resolved'`.
- Slice 09 admin resolution requires `disputes.resolved_at` when `status = 'resolved'`.
- Slice 09 admin cancellation requires `disputes.cancelled_at` when `status = 'cancelled'`.
- `disputes.resolution_type` can be set only by admin resolution service in slice 09.

## Creditos

- `credit_wallets.business_id` unique FK businesses(id).
- `credit_wallets.available_credits >= 0`.
- `credit_wallets.blocked_credits >= 0`.
- `credit_wallets.consumed_credits >= 0`.
- Balance de creditos nunca puede ser negativo.
- `credit_wallets` puede crearse lazy/idempotente en `slice_03_ads_marketplace` para negocio aprobado si no existe; inicia con balances cero y no inventa creditos.
- Ledger de creditos append-only.
- Cada movimiento debe tener `reason`, `source`, `created_by`, `reference_type`, `reference_id`.
- `credits_ledger.amount > 0`.
- `credits_ledger.reason` not null.
- `credits_ledger.source` not null.
- `credits_ledger.reference_type` not null.
- `credits_ledger.reference_id` not null.
- `credits_ledger.notes` es opcional y no reemplaza `reason`.
- `hold` requiere `related_ad_id`.
- `hold` requiere `reference_type = 'ad'` y `reference_id = related_ad_id`.
- `release` requiere `related_ad_id` y debe referenciar un hold previo no consumido/liberado.
- `consume` requiere `related_ad_id`, `related_order_id` y payment confirmation previa del negocio.
- Publicar anuncio descuenta de available y suma a blocked.
- Orden expirada/cancelada antes de pago confirmado descuenta de blocked y suma a available.
- Confirmacion de pago del negocio descuenta de blocked y suma a consumed.
- Confirmacion de pago del negocio debe crear ledger `consume` con `reason = business_confirmed_payment_received`, `source = orders`, `reference_type = order` y `reference_id = orders.id`.
- Confirmacion de pago del negocio debe archivar el anuncio asociado con `ads.status = archived`.
- No puede existir doble consumo de creditos para una misma orden; el servicio debe detectar ledger `consume` existente por `related_order_id/reference_id`.
- Si un reporte de pago es rechazado por el negocio, los creditos siguen bloqueados y no se crea ledger `consume`.
- Compra Stripe requiere `stripe_checkout_session_id` unique.
- Compra manual requiere comprobante, metodo (`zelle` o `usdt_trc20`) y aprobacion/rechazo admin.
- Compra manual usa `file_assets.resource_type = credit_purchase` y `file_type = credit_purchase_proof`; `storage_path` nunca se expone.
- `credit_purchases.status` CHECK contra enum oficial.
- `credit_purchases.payment_method` CHECK contra enum oficial.
- `credit_purchases.idempotency_key` participa en unique parcial por `business_id` cuando no sea null.
- `credit_purchases.stripe_event_id`, `stripe_checkout_session_id` y `stripe_payment_intent_id` deben ser unique parciales cuando no sean null.
- `credit_purchases.admin_note` es obligatorio para approve/reject manual.
- Compra on-chain Base usa `payment_method = base_usdc_onchain`.
- Compra on-chain Base requiere `chain_id = 8453`, `network = base_mainnet`, `token_symbol = USDC`, `token_contract_address = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`, `token_decimals = 6`.
- Compra on-chain Base requiere `destination_wallet_address`, `expected_amount_units` y `expires_at`.
- `expected_amount_units` y `tx_amount_units` deben usar `numeric(78,0)`.
- EVM values (`token_contract_address`, `destination_wallet_address`, `tx_hash`, `tx_from_address`, `tx_to_address`) deben persistirse/compararse normalizados lowercase; constraints o queries deben usar `lower(...)` o politica canonica equivalente.
- `credit_purchase_onchain_payments(chain_id, tx_hash, tx_log_index)` debe ser unique.
- `credit_purchase_onchain_payments.tx_amount_units > 0`.
- No puede existir doble ledger `purchase` para el mismo `related_credit_purchase_id`.
- `credited` requiere ledger `purchase` y `credited_at`.
- `base_usdt_onchain` no es metodo activo MVP.
- Founder access usa campos canonicos en `businesses`: `founder_status`, `founder_started_at`, `founder_expires_at`; tabla `founder_access` no es activa en MVP.
- Founder access requiere fecha de inicio, fecha de expiracion y limite de riesgo.
- `referral_codes.business_id` unique FK businesses(id).
- `referral_codes.code` unique.
- `referral_events.referrer_business_id` y `referred_business_id` FK businesses(id).
- `referral_events.referrer_business_id <> referral_events.referred_business_id`.
- `referral_events.related_credit_purchase_id` unique parcial cuando no sea null.
- `referral_events.referred_business_id` unique parcial mientras status in (`pending`, `approved`, `rewarded`).
- `referral_bonus` requiere `related_referral_id`, `related_credit_purchase_id`, `reference_type = referral_event` y `reference_id = referral_events.id`.
- `refund` y `adjustment` en `credits_ledger.type` son legacy/no validos; usar `release` y `admin_adjustment`.

## Admin y auditoria

- `audit_logs` append-only.
- `audit_logs.actor_user_id`, `event_type`, `resource_type`, `resource_id`, `request_id`, `created_at` obligatorios.
- `audit_logs.reason` obligatorio para acciones admin sensibles.
- Acciones admin sensibles requieren reason no vacio.
- Ajustes manuales de credito requieren doble registro: ledger + audit log.
- Resolver disputas requiere reason no vacio, `dispute_events` y audit log.
- `system_metrics` no es tabla activa en slice 09; las metricas admin son read model calculado desde tablas existentes.

## Staff interno

- `staff_profiles.id` uuid primary key.
- `staff_profiles.user_id` FK users(id).
- `staff_profiles.staff_role` CHECK IN (`support_agent`, `support_lead`, `operations_readonly`, `admin`, `super_admin`).
- `staff_profiles.status` CHECK IN (`active`, `suspended`, `revoked`).
- `staff_profiles.created_by_super_admin_id` FK users(id) not null.
- `staff_profiles.reason` obligatorio cuando `status in ('suspended', 'revoked')`.
- `staff_profiles.suspended_at` obligatorio cuando `status = 'suspended'`.
- `staff_profiles.revoked_at` obligatorio cuando `status = 'revoked'`.
- Solo puede existir un `staff_profiles.status = active` por `user_id`.
- `staff_permissions.staff_profile_id` FK staff_profiles(id).
- `staff_permissions.permission` CHECK contra permisos canonicos de staff.
- `staff_permissions.scope` CHECK IN (`assigned_only`, `queue_scope`, `category_scope`, `global_readonly`).
- `staff_permissions.status` CHECK IN (`active`, `revoked`).
- `staff_permissions.reason` not null.
- Solo puede existir un permiso activo por `(staff_profile_id, permission, scope, scope_value)`.
- `staff_invites.status` CHECK IN (`pending`, `accepted`, `expired`, `revoked`).
- `staff_invites.reason` not null.
- `staff_invites.expires_at` not null.
- `staff_invites.invite_code_hash` puede existir, pero nunca token/codigo plano.
- Ninguna constraint staff debe permitir hard delete de usuarios, tickets o audit.

## Integridad operacional

- Toda llamada mutante expuesta por API debe aceptar o generar idempotency key cuando pueda repetirse.
- Procesos async deben ser reentrantes.
- Workers deben usar locks con TTL para evitar doble procesamiento.
- Migraciones deben ser reversibles o tener plan de rollback documentado.

## Jobs y notificaciones

- `job_runs.job_type` CHECK contra enum oficial.
- `job_runs.status` CHECK contra enum oficial.
- `job_runs.job_type = expire_and_escalate_orders` es el job principal de slice 10.
- `job_runs.job_name` no es columna valida activa.
- `job_runs.lock_acquired` not null default false.
- `job_runs.attempts >= 0`.
- `job_runs.duration_ms >= 0` cuando no sea null.
- `job_runs.processed_count >= 0`.
- `job_runs.changed_count >= 0`.
- `job_runs.skipped_count >= 0`.
- `job_runs.failed_count >= 0`.
- `job_runs.finished_at` debe existir cuando `status in ('finished', 'failed', 'skipped', 'lock_not_acquired')`.
- `job_runs.error_code` debe existir cuando `status = failed`.
- `job_runs.error_message_safe` no debe contener stack traces, SQL, tokens, secretos, `storage_path`, `account_value` ni instrucciones completas.
- `job_runs.lock_key` no debe contener secretos.
- `notification_jobs.notification_type` CHECK contra enum oficial.
- `notification_jobs.event_type` es legacy/no valido para nuevas migraciones.
- `notification_jobs.status` CHECK contra enum oficial.
- `notification_jobs.attempts >= 0`.
- `notification_jobs.max_attempts > 0`.
- `notification_jobs.sent_at` solo existe cuando `status = sent`.
- `notification_jobs.failed_at` debe existir cuando `status = failed`.
- `notification_jobs.dedupe_key` unique para no duplicar recordatorios por recurso, tipo y ventana.
- Si `notification_jobs.recipient_user_id` es null, `recipient_role` debe estar presente.
- `notification_jobs.metadata_json` no debe contener `storage_path`, `account_value`, instrucciones completas, signed URLs, tokens, secretos, evidencia privada ni promesas de fondos.

## Business intake y soporte

- `business_intake_requests.status` CHECK contra enum oficial activo de intake MVP (`draft`, `submitted`, `accepted`, `rejected`).
- `business_intake_requests.operation` CHECK IN (`buy_usd`, `sell_usd`, `both`).
- `business_intake_requests.telegram_user_id` not null.
- `business_intake_requests.telegram_chat_id` not null.
- `business_intake_requests.contact_phone` nullable hasta recibir WhatsApp escrito por el solicitante.
- `business_intake_requests.business_phone` nullable hasta completar formulario; no reemplaza `contact_phone`.
- `business_intake_requests.last_step` not null default `start`.
- `business_intake_requests.last_step` debe validarse contra el enum canonico de pasos de 14D2; no se aceptan pasos libres.
- `business_intake_requests.last_update_id` nullable; si existe participa en idempotencia Telegram por `telegram_chat_id + last_update_id`.
- El webhook Telegram debe devolver `200 OK` para errores recuperables del usuario y no debe depender de retries de Telegram para corregir input.
- `business_intake_requests.min_amount_usd > 0` cuando no sea null.
- `business_intake_requests.max_amount_usd >= min_amount_usd` cuando ambos existan.
- `business_intake_requests.admin_reason` obligatorio cuando `status in ('accepted', 'rejected')`.
- `business_intake_requests.reviewed_by_admin_id` FK users(id) cuando reviewed_at no sea null.
- `business_intake_requests.created_business_id` FK businesses(id) nullable; no implica negocio aprobado automaticamente.
- `file_assets.resource_type = business_intake` para documentos de intake.
- `file_assets.file_type = intake_document` para todos los documentos de intake.
- MIME permitido para intake: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`.
- `file_assets.size_bytes <= 5242880` para intake.
- Documentos Telegram de intake deben deduplicarse por `business_intake_requests.telegram_chat_id + telegram_update_id + telegram_file_unique_id/file_id`; el storage no debe duplicar un archivo para el mismo update.
- `telegram_file_id`, `telegram_file_unique_id` y `document_kind` pueden vivir en metadata privada de `file_assets`, nunca en respuestas publicas con URLs directas.
- Video queda post-MVP y `video/*` debe rechazarse con `BOT_UPLOAD_INVALID`.
- `support_tickets.status` CHECK contra enum oficial.
- `support_tickets.scope` CHECK contra enum oficial.
- `support_tickets.requester_user_id` FK users(id).
- `support_tickets.requester_role` CHECK contra roles oficiales.
- `support_tickets.requester_surface` CHECK IN (`client_mini_app`, `business_mini_app`, `admin_web`).
- `support_tickets.business_id` FK businesses(id) nullable.
- `support_tickets.order_id` FK orders(id) nullable.
- `support_tickets.ad_id` FK ads(id) nullable.
- `support_tickets.credit_purchase_id` FK credit_purchases(id) nullable.
- `support_tickets.dispute_id` FK disputes(id) nullable.
- `support_tickets.ad_id` solo se permite cuando `scope = business_ad`.
- `support_tickets.credit_purchase_id` solo se permite cuando `scope = business_credit`.
- `support_tickets.order_id` solo se permite cuando `scope in ('client_order', 'business_order')`.
- `support_tickets.dispute_id` en 20B solo referencia disputa existente; soporte no crea ni resuelve disputa.
- `support_messages.ticket_id` FK support_tickets(id).
- `support_messages.sender_user_id` FK users(id).
- `support_messages.sender_role` CHECK contra roles oficiales.
- `support_messages.visibility` CHECK contra enum oficial.
- `support_ticket_events.ticket_id` FK support_tickets(id).
- `file_assets.resource_type IN ('support_ticket', 'support_message')` para adjuntos de soporte.
- `file_assets.file_type = support_attachment` para adjuntos de soporte.
- MIME permitido para adjuntos de soporte: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`.
- Tamano maximo de adjuntos de soporte: 5 MB.
- `storage_path` nunca se expone en API publica, frontend, logs ni audit metadata.
## Observability constraints - slice 24

La futura tabla `observability_events` debe cumplir:

- `event_id` unico.
- `expires_at` obligatorio.
- `severity` limitado a `debug|info|warn|error`.
- `surface` limitado a superficies contratadas.
- `duration_ms >= 0` cuando exista.
- `status_code` entre `100` y `599` cuando exista.
- `route_template` no puede ser URL cruda con query sensible.
- `metadata_json` debe estar redaccionado antes de persistir.

Prohibido persistir tokens, secrets, `storage_path`, `account_value`, signed URLs, full tx hash, documentos completos o mensajes completos.
