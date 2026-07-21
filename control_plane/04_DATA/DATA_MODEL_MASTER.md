# DATA_MODEL_MASTER.md

This is the canonical MVP data model. Detailed SQL migrations must follow this file and ENUMS_AND_STATUS_MASTER.md.

## users

- id
- telegram_id
- username
- first_name
- last_name
- phone
- role
- status
- trust_level
- orders_created_count
- orders_completed_count
- orders_expired_count
- created_at
- updated_at
- last_seen_at

Rules:
- `users.status = restricted` representa suspension operacional de usuario en 20A.
- `users.status = blocked` representa bloqueo fuerte; no implica borrar negocios, ordenes, links ni audit.
- `users.status = dormant` representa usuario inactivo/reactivable por admin segun contrato.
- Cambios de estado admin requieren reason, idempotencia y audit; reason no se agrega como columna de `users` en MVP.
- Admin user list/detail debe enmascarar `phone` y `telegram_id` por defecto.

## businesses

- id
- owner_user_id
- business_name
- rif
- address
- phone
- country
- verification_status
- trust_level
- reputation_tier
- risk_level
- min_order_amount_usd
- max_order_amount_usd
- daily_limit_usd
- active_order_limit
- rating_avg
- ratings_count
- completed_orders_count
- business_failure_orders_count
- lost_disputes_count
- disputes_count
- success_rate
- average_delivery_seconds
- reputation_calculated_at
- evasion_reports_count
- referral_code
- referral_credits_earned
- founder_status
- founder_started_at
- founder_expires_at
- created_at
- updated_at
- approved_at

## business_access_links

Vinculo canonico entre persona/Telegram y negocio para acceso a Mini App Negocio.

- id
- business_id
- user_id
- telegram_id_snapshot
- role_in_business
- status
- linked_by_admin_id
- linked_at
- suspended_at
- blocked_at
- revoked_at
- reason
- created_at
- updated_at

Rules:
- El acceso a `business_mini_app` requiere `business_access_links.status = active`.
- `telegram_id_snapshot` es snapshot de auditoria; la identidad activa se valida contra `users.telegram_id` e initData firmado.
- MVP solo permite `role_in_business = owner` para operar. `operator` queda reservado para contrato futuro.
- Suspender/revocar/bloquear el link no borra el negocio ni necesariamente bloquea al usuario.
- Bloquear usuario no borra el link ni el negocio; impide que ese usuario use NODO segun auth policy.
- Slice 20A permite listar links por `business_id` y por `user_id` desde Admin Web.

## business_verification_submissions

- id
- business_id
- submitted_by_user_id
- status
- submitted_data_json
- admin_reviewed_by_user_id
- admin_reason
- submitted_at
- reviewed_at
- created_at
- updated_at

## business_payment_methods

- id
- business_id
- method_type
- network
- account_value
- account_masked
- holder_name
- verified_status
- active
- created_at
- updated_at

Exposure rules:

- Full `account_value` is sensitive and never returned by business payment method list/selectors.
- Mini App Negocio may receive only safe selector fields: id, derived label, method displays, limits and masked account metadata.
- Management/approval is admin-controlled in 14B; business owners read approved active methods only.

## ads

- id
- business_id
- payment_method_id
- payment_method
- delivery_method
- rate_bs_per_usd
- amount_min_usd
- amount_max_usd
- required_credits
- status
- credit_hold_ledger_id
- credit_consumed_ledger_id
- created_at
- updated_at
- activated_at
- expires_at
- rate_updated_at

## credit_wallets

- id
- business_id
- available_credits
- blocked_credits
- consumed_credits
- lifetime_purchased_credits
- lifetime_bonus_credits
- lifetime_adjusted_credits
- created_at
- updated_at

## orders

- id
- public_order_code
- ad_id
- business_id
- remitter_user_id
- status
- idempotency_key
- completion_reason
- cancel_reason
- dispute_reason
- amount_usd
- rate_snapshot
- amount_bs_calculated
- business_name_snapshot
- receiver_data_json
- payment_method_snapshot
- delivery_method_snapshot
- min_amount_snapshot
- max_amount_snapshot
- payment_instructions_snapshot
- payment_data_revealed_at
- payment_data_revealed_by
- expires_at
- payment_report_deadline_at
- payment_report_extension_used_at
- business_response_warning_at
- business_response_deadline_at
- delivery_warning_at
- delivery_deadline_at
- auto_complete_warning_12h_at
- auto_complete_warning_23h_at
- auto_complete_at
- extension_used
- paid_reported_at
- payment_confirmed_at
- delivered_at
- completed_at
- created_at
- updated_at

Slice 06 notes:

- `payment_confirmed_at` se setea solo al confirmar recepcion real del pago por el negocio.
- `delivery_warning_at` y `delivery_deadline_at` se setean al pasar a `payment_confirmed`.
- `delivered_at`, `auto_complete_warning_12h_at`, `auto_complete_warning_23h_at` y `auto_complete_at` se setean al pasar a `delivered`.
- `payment_rejected` no vuelve automaticamente a `waiting_payment`.

## payment_reports

- id
- order_id
- reported_by_user_id
- status
- idempotency_key
- payment_type
- payment_reference
- payment_sender_name
- payment_sender_account_masked
- tx_hash
- network
- payment_amount
- proof_file_id
- report_payload_hash
- admin_notes
- created_at
- updated_at

Slice 06 notes:

- Confirmar pago por negocio cambia `status` de `submitted` a `accepted`.
- Rechazar reporte por negocio cambia `status` de `submitted` a `rejected`.
- Slice 06 no crea reportes nuevos; opera sobre el latest submitted report de la orden.
- `corrected` queda reservado para flujo futuro.

## messages

- id
- order_id
- sender_user_id
- sender_role
- body
- visibility
- status
- idempotency_key
- created_at
- updated_at
- deleted_at

Slice 07 notes:

- `messages` is the canonical chat table.
- `chat_messages` is legacy/non-valid naming and must not be used for new migrations.
- Messages belong to an order and are visible only to authorized parties/admin.

## message_attachments

- id
- message_id
- order_id
- file_asset_id
- uploaded_by_user_id
- file_type
- mime_type
- size_bytes
- status
- created_at
- updated_at
- deleted_at

## credits_ledger

- id
- business_id
- type
- amount
- balance_available_before
- balance_available_after
- balance_blocked_before
- balance_blocked_after
- balance_consumed_before
- balance_consumed_after
- related_ad_id
- related_order_id
- related_referral_id
- related_credit_purchase_id
- reason
- source
- reference_type
- reference_id
- notes
- created_by
- created_at

Slice 06 consume ledger:

- `type = consume`
- `amount = ads.required_credits`
- `related_ad_id = orders.ad_id`
- `related_order_id = orders.id`
- `reason = business_confirmed_payment_received`
- `source = orders`
- `reference_type = order`
- `reference_id = orders.id`
- `created_by = business owner id`

## credit_purchases

- id
- business_id
- package_code
- credits_amount
- price_usd
- payment_method
- status
- idempotency_key
- stripe_checkout_session_id
- stripe_payment_intent_id
- stripe_event_id
- manual_payment_reference
- manual_tx_hash
- manual_network
- chain_id
- network
- token_symbol
- token_contract_address
- token_decimals
- expected_amount_units
- destination_wallet_address
- verification_status
- verification_source
- proof_file_id
- approved_by_admin_id
- rejected_by_admin_id
- admin_note
- created_at
- updated_at
- paid_at
- approved_at
- rejected_at
- failed_at
- expired_at
- detected_at
- verified_at
- credited_at
- expires_at

Slice 19 on-chain notes:

- `base_usdc_onchain` uses Base mainnet `chain_id = 8453`.
- USDC Base contract is `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`.
- USDT Base is not active in MVP.
- `expected_amount_units` uses `numeric(78,0)` and stores USDC minor units with 6 decimals. Do not use float.
- `destination_wallet_address` comes from `NODO_CREDIT_RECEIVING_WALLET_BASE`.
- EVM values (`token_contract_address`, `destination_wallet_address`, `tx_hash`, `tx_from_address`, `tx_to_address`) must be stored and compared normalized lowercase, or with an equivalent canonical normalization policy.
- No private key or seed phrase is stored.

## credit_purchase_onchain_payments

- id
- credit_purchase_id
- business_id
- chain_id
- network
- token_symbol
- token_contract_address
- token_decimals
- tx_hash
- tx_from_address
- tx_to_address
- tx_block_number
- tx_log_index
- tx_amount_units
- confirmations
- verification_source
- verification_status
- failure_code
- detected_at
- verified_at
- credited_at
- created_at
- updated_at

Rules:

- Unique `(chain_id, tx_hash, tx_log_index)`.
- `tx_amount_units` uses `numeric(78,0)` and stores token minor units.
- EVM address/hash fields must be normalized lowercase before persistence and comparison.
- Used to prevent double credit from the same on-chain transfer.
- Raw provider responses, RPC keys, private keys and seed phrases are never stored here.

## referral_codes

- id
- business_id
- code
- status
- created_at
- updated_at
- disabled_at

## referral_events

- id
- referral_code_id
- referrer_business_id
- referred_business_id
- related_credit_purchase_id
- status
- credits_awarded
- reject_reason
- created_at
- approved_at
- rewarded_at
- rejected_at

Legacy/non-valid:

- `referrals` must not be used for new migrations. Use `referral_codes` and `referral_events`.
- `founder_access` table must not be used for MVP. Founder access uses fields on `businesses`.

## ratings

- id
- order_id
- business_id
- rater_user_id
- stars
- created_at

Rules:

- Un solo rating por orden completada.
- `stars` es entero entre 1 y 5.
- MVP no persiste comentarios, resenas textuales, titulos ni cuerpos libres.
- El cliente que califica debe ser `orders.remitter_user_id`; esta regla se
  valida en servicio antes de escribir.
- Admin no puede crear ni editar ratings.
- Los agregados de reputacion en `businesses` son reconstruibles desde ratings,
  ordenes, eventos y disputas.

## disputes

- id
- order_id
- opened_by_user_id
- opened_by_role
- previous_order_status
- reason
- description
- status
- resolution_type
- resolution
- resolution_reason
- resolved_by_admin_id
- created_at
- updated_at
- resolved_at
- cancelled_at

Slice 09 admin resolution notes:

- `resolution_type` is set only by `POST /api/v1/admin/disputes/{id}/resolve`.
- `resolution_reason` is required for terminal admin resolution.
- `resolved_by_admin_id` is required when `status = resolved`.
- `cancelled_at` is required when `status = cancelled`.
- Admin resolution must create `dispute_events` and audit logs.
- Credit/ad/order effects are governed by `DISPUTE_RESOLUTION_MASTER.md`.

## dispute_events

- id
- dispute_id
- order_id
- actor_user_id
- actor_role
- event_type
- old_status
- new_status
- reason
- metadata_json
- created_at

## audit_logs

- id
- actor_user_id
- actor_role
- event_type
- resource_type
- resource_id
- old_value_json
- new_value_json
- reason
- request_id
- job_id
- ip_hash
- user_agent
- metadata_json
- created_at

## job_runs

- id
- job_type
- status
- lock_key
- lock_acquired
- attempts
- started_at
- finished_at
- duration_ms
- processed_count
- changed_count
- skipped_count
- failed_count
- error_code
- error_message_safe
- metadata_json
- created_at
- updated_at

Rules:

- `job_type` is canonical; `job_name` is not a valid active column.
- Initial canonical `job_type`: `expire_and_escalate_orders`.
- `status` uses `job_runs.status` enum.
- `error_message_safe` must not contain stack traces, SQL, tokens, secrets,
  `storage_path`, `account_value` or full payment instructions.
- `lock_key` must not contain secrets.

## app_metadata

- id
- key
- value_json
- created_at
- updated_at

## sessions

- id
- user_id
- refresh_token_hash
- status
- access_token_jti
- created_at
- updated_at
- expires_at
- revoked_at
- last_used_at
- ip_hash
- user_agent

## notification_jobs

- id
- notification_type
- recipient_user_id
- recipient_role
- order_id
- business_id
- dispute_id
- status
- scheduled_for
- sent_at
- failed_at
- attempts
- max_attempts
- last_error_code
- dedupe_key
- metadata_json
- created_at
- updated_at

Rules:

- `notification_type` is canonical; legacy `event_type` is not valid for new
  notification job migrations.
- `recipient_user_id` is nullable for role/queue notifications; if null,
  `recipient_role` must be present.
- `status` uses `notification_jobs.status` enum.
- `dedupe_key` prevents duplicate reminders for the same resource, notification
  type and time window.
- `metadata_json` is private/masked and must not contain `storage_path`,
  `account_value`, full payment instructions, signed URLs, tokens, secrets,
  raw evidence or guarantees of funds.

## file_assets

- id
- owner_user_id
- resource_type
- resource_id
- file_type
- storage_path
- mime_type
- size_bytes
- created_at
- deleted_at

For payment evidence in `slice_05_payment_instructions_reports`:

- `resource_type = payment_report`
- `resource_id = payment_reports.id`
- `file_type = payment_evidence`
- `owner_user_id = orders.remitter_user_id`
- `storage_path` is private and never exposed in public API, frontend, logs or audit metadata.

For message attachments in `slice_07_chat_disputes`:

- `resource_type = message`
- `resource_id = messages.id` when attached, or a service-held pending message id during upload flow
- `file_type = message_attachment`
- `owner_user_id = uploaded_by_user_id`
- `storage_path` is private and never exposed in public API, frontend, logs or audit metadata.

For manual credit purchase proofs in `slice_08_credits_referrals`:

- `resource_type = credit_purchase`
- `resource_id = credit_purchases.id`
- `file_type = credit_purchase_proof`
- `owner_user_id = business owner id`
- `storage_path` is private and never exposed in public API, frontend, logs or audit metadata.

For business intake documents in `slice_14D_business_intake_bot`:

- `resource_type = business_intake`
- `resource_id = business_intake_requests.id`
- `file_type = intake_document`
- `owner_user_id` must reference the Telegram applicant user when one exists; if no user exists yet, the backend must create/link a safe user record before persisting the file or block the upload.
- `storage_path` is private and never exposed in public API, frontend, logs or audit metadata.
- Telegram document metadata for slice 14D2 must be stored only in private service metadata, not public responses:
  - `telegram_update_id`
  - `telegram_file_id`
  - `telegram_file_unique_id` when Telegram provides it
  - `document_kind`
  - original Telegram MIME/type
- `telegram_file_id` and `telegram_file_unique_id` must not be treated as public download URLs.

## business_metrics

- business_id
- reputation_tier
- completed_orders_count
- business_failure_orders_count
- cancelled_orders_count
- disputes_count
- lost_disputes_count
- avg_response_time
- rating_avg
- ratings_count
- success_rate
- average_delivery_seconds
- monthly_volume_reported
- evasion_reports_count

`business_metrics` sigue siendo un read model conceptual en MVP; Slice 42A no
crea una tabla competidora. Los agregados persistidos viven en `businesses` y
deben poder reconstruirse.

## admin_system_metrics_read_model

This is not a table in MVP. Slice 09 metrics are calculated from existing
tables unless a future contract explicitly creates persisted metrics.

Sources:

- orders
- businesses
- credit_purchases
- disputes
- audit_logs
- business_metrics
- job_runs
- app_metadata

Forbidden for slice 09:

- creating a competing `system_metrics` table without updating constraints,
  indexes, migrations and source-of-truth docs.

## staff_profiles

Source of truth for internal staff delegation. It augments `users` but does not replace `users.role`.

Columns:
- id
- user_id
- staff_role
- status
- display_name
- created_by_super_admin_id
- activated_by_super_admin_id
- suspended_by_super_admin_id
- revoked_by_super_admin_id
- activated_at
- suspended_at
- revoked_at
- reason
- created_at
- updated_at

Rules:
- `staff_role` values: `support_agent`, `support_lead`, `operations_readonly`, `admin`, `super_admin`.
- `status` values: `active`, `suspended`, `revoked`.
- Effective staff access requires `users.status = active` and `staff_profiles.status = active`.
- Revoking staff does not block or delete the user.

## staff_permissions

Granular internal permissions for staff.

Columns:
- id
- staff_profile_id
- permission
- scope
- scope_value
- status
- granted_by_super_admin_id
- revoked_by_super_admin_id
- revoked_at
- reason
- created_at
- updated_at

Rules:
- Permissions are limited to `INTERNAL_STAFF_MASTER.md`.
- Staff permissions cannot grant critical actions over users, businesses, credits, disputes, orders or ads.

## staff_invites

Invite/activation records for internal staff.

Columns:
- id
- target_user_id
- target_telegram_id
- target_username
- invite_code_hash
- staff_role
- status
- expires_at
- created_by_super_admin_id
- accepted_by_user_id
- accepted_at
- revoked_at
- expired_at
- reason
- created_at
- updated_at

Rules:
- No plaintext invite secret is persisted or returned after creation.
- `staff_activity` is not an MVP table; it is a read model from audit/events.

## business_intake_requests

- id
- telegram_user_id
- telegram_chat_id
- contact_phone
- business_phone
- referral_code
- status
- last_step
- last_update_id
- business_name
- responsible_name
- city
- operation
- banks_json
- methods_json
- min_amount_usd
- max_amount_usd
- schedule_text
- references_json
- submitted_at
- reviewed_by_admin_id
- reviewed_at
- admin_reason
- created_business_id
- linked_telegram_user_id
- created_at
- updated_at
- archived_at

Rules:
- Bot creates intake request only; it never creates active business.
- Active MVP statuses are `draft`, `submitted`, `accepted`, `rejected`.
- `contact_phone` comes only from Telegram shared contact.
- `business_phone` is the business operating phone declared in the form.
- Contact validation requires Telegram `contact.user_id == telegram_user_id`.
- `last_update_id` stores the latest Telegram update processed for idempotency.
- `last_step` stores the current guided form step; it is UI/conversation state, not an approval status.
- `last_step` values for slice 14D2 are canonical: `start`, `awaiting_contact`, `awaiting_business_name`, `awaiting_responsible_name`, `awaiting_city`, `awaiting_business_phone`, `awaiting_operation`, `awaiting_banks`, `awaiting_methods`, `awaiting_min_amount`, `awaiting_max_amount`, `awaiting_schedule`, `awaiting_references`, `awaiting_documents`, `submitted`.
- Each valid answer updates the relevant field immediately while `status = draft`; `status` changes to `submitted` only after final confirmation.
- `contact_phone` and `business_phone` remain separate columns and must not overwrite each other.
- Admin accept/reject requires reason.
- Documents use `file_assets.resource_type = business_intake` and `file_assets.file_type = intake_document`.
- Intake files allow only `image/jpeg`, `image/png`, `image/webp`, `application/pdf`, max 5 MB.
- Video is post-MVP and must not be accepted by slice 14D.

## support_tickets

- id
- requester_user_id
- requester_role
- requester_surface
- scope
- category
- status
- business_id
- order_id
- ad_id
- credit_purchase_id
- dispute_id
- subject
- priority
- assigned_support_user_id
- last_message_at
- escalated_at
- resolved_at
- closed_at
- created_at
- updated_at

Rules:
- Support tickets do not change order status by themselves.
- 20B does not create disputes from support.
- `dispute_id` may reference an existing dispute for context only; it does not imply support resolved or created a dispute.
- `ad_id` is allowed only for `scope = business_ad`.
- `credit_purchase_id` is allowed only for `scope = business_credit`.
- No `support_attachments` table in MVP; use `file_assets`.

## support_messages

- id
- ticket_id
- sender_user_id
- sender_role
- body
- visibility
- created_at
- updated_at
- deleted_at

Rules:
- Messages are visible only to ticket participants and authorized admin/support.
- Body must not be copied into audit metadata.
- Attachments for messages use `file_assets.resource_type = support_message`, `file_type = support_attachment`.

## support_ticket_events

- id
- ticket_id
- actor_user_id
- actor_role
- event_type
- from_status
- to_status
- reason
- metadata_json
- created_at

Rules:
- `metadata_json` must not contain storage paths, secrets, tokens, account values or private evidence.
- Assignment, escalation, resolve and close must create events.
## Observability operacional - slice 24

Tabla contratada futura: `observability_events`.

Uso:

- diagnostico operacional con TTL;
- reconstruccion estructurada sin video;
- busqueda Admin Web/support con masking;
- correlacion por `request_id`, `correlation_id`, `operation_id` y `session_id`.

No uso:

- audit formal durable;
- ledger financiero;
- fuente de verdad de negocio;
- almacenamiento de payloads privados.

Columnas canonicas y reglas completas viven en:

```txt
control_plane/09_SLICES/slice_24_observability_debuggability/DATA_CONTRACT.md
```
