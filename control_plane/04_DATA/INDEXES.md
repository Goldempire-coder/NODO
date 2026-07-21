# INDEXES.md

Indices obligatorios para sostener 200 negocios, 10,000 clientes y 2,000 ordenes activas/concurrentes.

## Usuarios

- `users(telegram_id)` unique.
- `users(status, created_at desc)`.
- `users(role, status)`.
- `users(phone)` parcial cuando `phone is not null` para busqueda admin.
- `lower(users.username)` parcial cuando `username is not null` para busqueda admin case-insensitive.

## Sesiones

- `sessions(user_id, status, created_at desc)`.
- `sessions(refresh_token_hash)` unique.
- `sessions(access_token_jti)` cuando exista.
- `sessions(expires_at)`.

## Negocios

- `businesses(owner_user_id)`.
- `businesses(verification_status, created_at desc)`.
- `businesses(verification_status, risk_level)`.
- `businesses(reputation_tier, completed_orders_count desc)` para lectura
  reputacional cuando exista query que lo justifique.
- `businesses(business_name)` o nombre normalizado cuando exista.
- `business_access_links(business_id, status)`.
- `business_access_links(user_id, status)`.
- `business_access_links(telegram_id_snapshot, status)`.
- `business_access_links(business_id, role_in_business, status)`.
- unique parcial `business_access_links(business_id, user_id, role_in_business)` where status = `active`.
- unique parcial `business_access_links(business_id)` where role_in_business = `owner` and status = `active`.
- `business_verification_submissions(business_id, status, created_at desc)`.
- `business_verification_submissions(status, submitted_at desc)`.
- `business_verification_submissions(admin_reviewed_by_user_id, reviewed_at desc)` cuando reviewed_by no sea null.
- `business_verification_submissions(business_id)` unique parcial cuando status = `pending`.
- `business_payment_methods(business_id, active)`.
- `business_payment_methods(business_id, method_type, network)`.
- `business_payment_methods(business_id, verified_status, active)` recomendado para `GET /api/v1/business/payment-methods`.
- `file_assets(resource_type, resource_id, created_at desc)`.
- `file_assets(owner_user_id, created_at desc)`.
- unique `ratings(order_id)`.
- `ratings(business_id, created_at desc)`.
- `ratings(rater_user_id, created_at desc)`.

## Anuncios y marketplace

- `ads(status, payment_method, delivery_method, rate_bs_per_usd desc)`.
- `ads(status, payment_method, delivery_method, amount_min_usd, amount_max_usd)`.
- `ads(business_id, status, created_at desc)`.
- `ads(expires_at)` para expiracion.
- Indice parcial para anuncios `active` no archivados.
- Indice parcial/constraint para evitar rangos solapados `active`/`paused` por `business_id`, `payment_method`, `delivery_method`.

## Ordenes

- `orders(remitter_user_id, created_at desc)`.
- `orders(business_id, created_at desc)`.
- `orders(status, created_at desc)`.
- `orders(business_id, status, created_at desc)`.
- `orders(remitter_user_id, status, created_at desc)`.
- `orders(public_order_code)` unique.
- `orders(idempotency_key, remitter_user_id)` unique parcial cuando idempotency_key no sea null.
- `orders(ad_id, status)` para validar un anuncio tomado por una orden activa.
- `orders(status, payment_report_deadline_at)` para expirar `waiting_payment`.
- `orders(status, business_response_warning_at)` para warning de `payment_reported`.
- `orders(status, business_response_deadline_at)` para disputa por negocio sin respuesta.
- `orders(status, delivery_warning_at)` para warning de `payment_confirmed`.
- `orders(status, delivery_deadline_at)` para disputa por no entregar.
- `orders(status, auto_complete_at)` para auto-complete de `delivered`.

## Pagos y evidencia

- `payment_reports(order_id, created_at desc)`.
- `payment_reports(order_id, status, created_at desc)`.
- `payment_reports(status, created_at desc)`.
- `payment_reports(reported_by_user_id, created_at desc)`.
- `payment_reports(reported_by_user_id, idempotency_key)` unique parcial cuando `idempotency_key is not null`.
- `payment_reports(order_id)` unique parcial para `status = submitted`.

## Chat y disputas

- `messages(order_id, created_at asc)`.
- `messages(order_id, sender_user_id, created_at desc)`.
- `messages(created_at desc)` para moderacion admin.
- `messages(sender_user_id, idempotency_key)` unique parcial cuando `idempotency_key is not null`.
- `message_attachments(order_id, created_at desc)`.
- `message_attachments(message_id, created_at asc)`.
- `message_attachments(file_asset_id)` unique.
- `disputes(status, created_at desc)`.
- `disputes(order_id)` unique parcial para disputa abierta.
- `disputes(order_id, status, created_at desc)`.
- `dispute_events(dispute_id, created_at asc)`.
- `dispute_events(order_id, created_at desc)`.

## Creditos

- `credit_wallets(business_id)` unique.
- `credits_ledger(business_id, created_at desc)`.
- `credits_ledger(type, created_at desc)`.
- `credits_ledger(reference_type, reference_id, created_at desc)`.
- `credits_ledger(reference_type, reference_id, type)`.
- `credits_ledger(related_ad_id)` parcial cuando no sea null.
- `credits_ledger(related_order_id, type)` parcial cuando `related_order_id` no sea null.
- `credit_purchases(business_id, status, created_at desc)`.
- `credit_purchases(stripe_checkout_session_id)` unique parcial cuando no sea null.
- `credit_purchases(stripe_payment_intent_id)` unique parcial cuando no sea null.
- `credit_purchases(stripe_event_id)` unique parcial cuando no sea null.
- `credit_purchases(manual_payment_reference)` unique parcial cuando exista.
- `credit_purchases(business_id, idempotency_key)` unique parcial cuando `idempotency_key` no sea null.
- `credit_purchases(payment_method, status, expires_at)` para watcher on-chain.
- `credit_purchases(chain_id, token_contract_address, status)` para verificacion on-chain.
- `credit_purchase_onchain_payments(credit_purchase_id, created_at desc)`.
- `credit_purchase_onchain_payments(business_id, created_at desc)`.
- `credit_purchase_onchain_payments(chain_id, tx_hash, tx_log_index)` unique.
- `credit_purchase_onchain_payments(verification_status, created_at desc)`.
- `referral_codes(code)` unique.
- `referral_codes(business_id)` unique.
- `referral_events(referrer_business_id, created_at desc)`.
- `referral_events(referred_business_id, created_at desc)`.
- `referral_events(referred_business_id)` unique parcial para status `pending`/`approved`/`rewarded`.
- `referral_events(related_credit_purchase_id)` unique parcial cuando no sea null.

## Auditoria

- `audit_logs(resource_type, resource_id, created_at desc)`.
- `audit_logs(actor_user_id, created_at desc)`.
- `audit_logs(event_type, created_at desc)`.
- `audit_logs(created_at desc)`.

## Staff interno

- `staff_profiles(user_id, status)`.
- `staff_profiles(staff_role, status, created_at desc)`.
- unique parcial `staff_profiles(user_id)` where status = `active`.
- `staff_permissions(staff_profile_id, status)`.
- `staff_permissions(permission, status)`.
- unique parcial `staff_permissions(staff_profile_id, permission, scope, scope_value)` where status = `active`.
- `staff_invites(status, expires_at)`.
- `staff_invites(target_user_id, status)` parcial cuando target_user_id no sea null.
- `staff_invites(target_telegram_id, status)` parcial cuando target_telegram_id no sea null.
- `staff_invites(lower(target_username), status)` parcial cuando target_username no sea null.

## Admin console read models

- Slice 09 admin metrics use existing indexes on `orders`, `businesses`,
  `credit_purchases`, `disputes`, `audit_logs`, `job_runs` and `app_metadata`.
- Do not create a `system_metrics` table/index in slice 09 unless a future
  contract changes the data model.
- Admin dispute resolution uses `disputes(status, created_at desc)`,
  `disputes(order_id, status, created_at desc)`, `dispute_events(dispute_id,
  created_at asc)`, `credits_ledger(reference_type, reference_id, type)` and
  `credits_ledger(related_order_id, type)`.

## Jobs y metadata

- `job_runs(job_type, status, created_at desc)`.
- `job_runs(lock_key)` parcial cuando lock_key no sea null.
- `job_runs(job_type, started_at desc)`.
- `notification_jobs(status, scheduled_for asc)`.
- `notification_jobs(notification_type, status, scheduled_for asc)`.
- `notification_jobs(dedupe_key)` unique.
- `notification_jobs(order_id, notification_type, created_at desc)` parcial cuando order_id no sea null.
- `notification_jobs(business_id, notification_type, created_at desc)` parcial cuando business_id no sea null.
- `notification_jobs(dispute_id, notification_type, created_at desc)` parcial cuando dispute_id no sea null.
- `app_metadata(key)` unique.

## Regla de aceptacion

Toda query que aparezca en una pantalla principal debe tener indice revisado antes de merge. Si el builder agrega una query sin indice o sin justificarlo, el slice queda bloqueado.

## Business intake y soporte

- `business_intake_requests(status, submitted_at desc)`.
- `business_intake_requests(telegram_user_id, created_at desc)`.
- `business_intake_requests(telegram_chat_id, created_at desc)`.
- unique parcial `business_intake_requests(telegram_chat_id, last_update_id)` cuando `last_update_id is not null`.
- `business_intake_requests(contact_phone, created_at desc)` parcial cuando contact_phone no sea null.
- `business_intake_requests(created_business_id)` parcial cuando created_business_id no sea null.
- `file_assets(resource_type, resource_id, created_at desc)` cubre documentos de intake.
- Si 14D2 persiste `telegram_file_unique_id`/`telegram_file_id` en metadata JSON, agregar indice/unique funcional o validacion transaccional equivalente para evitar duplicados por `resource_type = business_intake`, `resource_id`, `telegram_update_id` y `telegram_file_unique_id/file_id`.
- `support_tickets(requester_user_id, status, updated_at desc)`.
- `support_tickets(business_id, status, updated_at desc)` parcial cuando business_id no sea null.
- `support_tickets(order_id, created_at desc)` parcial cuando order_id no sea null.
- `support_tickets(ad_id, created_at desc)` parcial cuando ad_id no sea null.
- `support_tickets(credit_purchase_id, created_at desc)` parcial cuando credit_purchase_id no sea null.
- `support_tickets(dispute_id, created_at desc)` parcial cuando dispute_id no sea null.
- `support_tickets(assigned_support_user_id, status, updated_at desc)` parcial cuando assigned_support_user_id no sea null.
- `support_tickets(scope, category, status, priority, updated_at desc)`.
- `support_messages(ticket_id, created_at asc)`.
- `support_ticket_events(ticket_id, created_at asc)`.
- `file_assets(resource_type, resource_id, created_at desc)` cubre `business_intake`, `support_ticket` y `support_message`.
## Observability indexes - slice 24

Futuros indices requeridos para `observability_events`:

- unique `observability_events_event_id_uq` on `event_id`.
- `observability_events_request_id_idx` on `request_id`.
- `observability_events_correlation_id_idx` on `correlation_id`.
- `observability_events_operation_id_idx` on `operation_id`.
- `observability_events_session_id_idx` on `session_id`.
- `observability_events_surface_received_idx` on `(surface, received_at desc)`.
- `observability_events_resource_order_idx` on `order_id` where not null.
- `observability_events_resource_ticket_idx` on `ticket_id` where not null.
- `observability_events_resource_credit_idx` on `credit_purchase_id` where not null.
- `observability_events_expires_at_idx` on `expires_at` for cleanup.
