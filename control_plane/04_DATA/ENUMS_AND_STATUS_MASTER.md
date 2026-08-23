# ENUMS_AND_STATUS_MASTER.md

payment_method:
- zelle
- usdt_trc20

delivery_method:
- pago_movil_ve

user.role:
- remitter
- business_owner
- admin
- super_admin
- support

user.role post_mvp:
- business_operator
- support_readonly

user.role derived_only:
- guest

Regla:
- `guest` no se persiste en DB; representa una request sin sesion valida.
- `super_admin` si puede persistirse en DB para owner/sistema con permisos criticos.
- `support_agent`, `support_lead` y `operations_readonly` no son `users.role`; son `staff_profiles.staff_role`.

user.status:
- active
- restricted
- blocked
- dormant

Reglas:
- `active`: usuario puede usar superficies segun rol, RBAC y surface/session.
- `restricted`: usuario suspendido operacionalmente; no puede entrar a superficies sensibles ni operar, salvo contrato futuro explicito.
- `blocked`: bloqueo fuerte; no puede autenticar/operar ni refrescar sesion.
- `dormant`: usuario inactivo; puede reactivarse por admin si contrato lo permite.
- `suspend_user` en slice 20A setea `restricted`; no existe `users.status = suspended`.

session.status:
- active
- revoked
- expired

business.verification_status:
- pending
- approved
- rejected
- suspended
- blocked

business_access_link.status:
- active
- suspended
- revoked
- blocked

business_access_link.role_in_business:
- owner
- operator

Regla:
- `operator` queda reservado para futuro; en MVP/14B1 solo `owner` habilita Mini App Negocio.

business_verification_submission.status:
- pending
- approved
- rejected

business.trust_level:
- new
- basic
- plus
- pro
- premium

Regla:
- `trust_level` controla limites/capacidad interna y no es reputacion publica.

business.reputation_tier:
- new
- active
- reliable
- elite

Regla:
- `Pausado/Offline` y `No disponible` son presentaciones de disponibilidad, no
  valores persistidos de `reputation_tier`.

business.risk_level:
- normal
- watch
- under_review
- restricted
- high_risk

Regla:
- `risk_level` es interno y nunca se expone en contratos publicos.

ad.status:
- draft
- active
- in_order
- archived
- expired
- paused
- suspended

order.status:
- created
- waiting_payment
- payment_reported
- payment_rejected
- payment_confirmed
- delivered
- completed
- cancelled
- disputed

Regla C0:
- `payment_rejected` es estado persistente legacy/historico. Permanece en el
  enum para filas existentes, filtros, timeline y recuperacion Admin.
- Ninguna nueva accion del negocio desde `payment_reported` debe crearlo; el
  problema de pago abre `disputed`.
- Una fila historica `payment_rejected` no vuelve a `waiting_payment`; se escala
  a disputa.

order.completion_reason:
- manual_confirmed
- auto_completed_after_24h
- admin_resolved

order.cancel_reason:
- payment_not_reported_in_time
- remitter_cancelled_before_payment
- admin_cancelled

order.dispute_reason:
- business_no_payment_confirmation
- payment_not_received_or_incomplete
- business_confirmed_payment_but_not_delivered
- payment_mobile_not_received
- amount_incorrect
- wrong_receiver_data
- other

`payment_not_received_or_incomplete` corresponde al problema Zelle/USDT
reportado por el negocio desde `payment_reported`. `payment_mobile_not_received`
corresponde al flujo posterior de entrega de Pago Movil; no sustituye la razon
de problema con el pago inicial.

message.sender_role:
- remitter
- business_owner
- admin
- super_admin
- support

message.visibility:
- parties
- admin_only

message.status:
- visible
- hidden
- deleted

message_attachment.status:
- active
- deleted

dispute.status:
- open
- in_review
- resolved
- cancelled

dispute.resolution_type:
- remitter_favored
- business_favored
- cancelled
- completed
- keep_under_review

Regla slice_07:
- Slice 07 crea disputas `open`.
- `in_review`, `resolved` y `cancelled` no son usados por slice 07 para resolver disputas.
- `dispute.resolution_type` no debe usarse para mutaciones en slice 07.

Regla slice_09:
- Slice 09 puede usar `dispute.resolution_type` solo mediante `POST /api/v1/admin/disputes/{id}/resolve`.
- `remitter_favored`, `business_favored`, `cancelled`, `completed` y `keep_under_review` son los valores canonicos para resolucion admin.
- No crear alias como `remitter_wins`, `business_wins`, `mutual_cancel` o `no_action_evidence_insufficient` sin actualizar este archivo.

payment_report.status:
- submitted
- corrected
- rejected
- accepted

Regla slice_06:
- `submitted -> accepted` cuando el negocio confirma pago recibido.
- `submitted -> rejected` queda reservado para datos/operaciones legacy. La
  apertura nueva de disputa desde `payment_reported` conserva `submitted` hasta
  resolucion Admin.
- `corrected` queda para flujo futuro.

credits_ledger.type:
- purchase
- founder_free_use
- referral_bonus
- hold
- release
- consume
- expire
- admin_adjustment

credit_purchase.payment_method:
- stripe_checkout
- zelle_manual_admin_approved
- usdt_manual_admin_approved
- base_usdc_onchain (legacy: solo local/staging o fallback manual/Admin; no
  auto-credito con trafico real controlado)
- base_usdc_contract (flujo normal futuro)

credit_purchase.payment_method post_mvp_or_disabled:
- base_usdt_onchain (no activo MVP)

credit_purchase.status:
- created
- pending_payment
- pending_manual_review
- pending_onchain_confirmation
- detected
- verified
- credited
- under_review
- paid
- approved
- rejected
- verification_failed
- failed
- expired

business.founder_status:
- active
- expired
- revoked

referral_code.status:
- active
- disabled

referral_event.status:
- pending
- approved
- rewarded
- rejected

job_runs.job_type:
- expire_and_escalate_orders
- verify_base_usdc_credit_purchases

job_runs.status:
- started
- finished
- failed
- skipped
- lock_not_acquired

notification_jobs.notification_type:
- order_payment_deadline_warning
- order_cancelled_payment_not_reported
- order_business_response_warning
- order_disputed_business_no_payment_confirmation
- order_delivery_warning
- order_disputed_business_confirmed_payment_but_not_delivered
- delivered_reminder_immediate
- delivered_reminder_12h
- delivered_reminder_23h
- order_auto_completed_after_24h
- ad_expired
- founder_access_expired
- admin_alert_test
- admin_alert_business_intake_submitted
- admin_alert_dispute_opened

notification_jobs.status:
- pending
- sent
- failed
- skipped
- cancelled

Prohibidos:
- usdt como payment_method
- pago_movil como delivery_method
- business como user.role
- completed_auto como order.status
- founder_free como credits_ledger.type
- credit_purchase_pending como tabla o status
- refund como credits_ledger.type activo
- adjustment como credits_ledger.type activo
- referrals como tabla activa nueva
- founder_access como tabla activa MVP
- job_name como columna activa en job_runs
- event_type como columna activa nueva en notification_jobs

surface.name:
- client_mini_app
- business_mini_app
- admin_web
- business_intake_bot

business_intake.status:
- draft
- submitted
- accepted
- rejected

business_intake.status post_mvp_or_legacy:
- under_review
- archived

Regla:
- Slice 14D usa solo `draft`, `submitted`, `accepted`, `rejected`.
- `under_review` y `archived` no son estados activos para el build 14D.

business_intake.operation:
- buy_usd
- sell_usd
- both

business_intake.last_step:
- start
- awaiting_referral_code
- awaiting_whatsapp_phone
- awaiting_contact # legacy/internal only; no activo en Bot Registro Negocios MVP
- awaiting_business_name
- awaiting_responsible_name
- awaiting_city
- awaiting_business_phone
- awaiting_operation
- awaiting_banks
- awaiting_methods
- awaiting_min_amount
- awaiting_max_amount
- awaiting_schedule
- awaiting_references
- awaiting_documents
- submitted

business_intake.file_assets.file_type:
- intake_document

business_intake.document_kind:
- identity_document
- rif_document
- local_image
- social_reference
- other_reference

Regla:
- `file_assets.file_type` para intake siempre es `intake_document`.
- `document_kind` es clasificacion de flujo/UI/audit, no `file_assets.file_type`.
- Video/local media en movimiento queda post-MVP y debe rechazarse en 14D.

support_ticket.status:
- open
- waiting_user
- waiting_support
- escalated
- resolved
- closed

support_ticket.scope:
- client_general
- client_order
- business_general
- business_order
- business_ad
- business_credit
- admin_internal

support_ticket.category:
- technical_issue
- account_access
- order_help
- payment_report_help
- business_access
- credits_help
- suspicious_activity
- other

support_message.visibility:
- participants
- support_internal
- admin_internal

support_event.type:
- support_ticket_created
- support_message_created
- support_attachment_uploaded
- support_attachment_viewed
- support_ticket_assigned
- support_ticket_escalated
- support_ticket_linked_to_dispute
- support_ticket_resolved
- support_ticket_closed

staff_profile.staff_role:
- support_agent
- support_lead
- operations_readonly
- admin
- super_admin

staff_profile.status:
- active
- suspended
- revoked

staff_permission.permission:
- view_support_queue
- view_assigned_support_tickets
- reply_support_ticket
- assign_support_ticket
- escalate_support_ticket
- resolve_support_ticket
- close_support_ticket
- view_support_attachment
- view_users_masked
- view_businesses_masked
- view_orders_masked
- view_audit_limited
- view_metrics_limited

staff_permission.scope:
- assigned_only
- queue_scope
- category_scope
- global_readonly

staff_permission.status:
- active
- revoked

staff_invite.status:
- pending
- accepted
- expired
- revoked

staff_audit_event.type:
- staff_invite_created
- staff_invite_expired
- staff_activated
- staff_suspended
- staff_revoked
- staff_permissions_updated
- staff_activity_viewed
- staff_ticket_assigned
- staff_access_denied

Prohibidos slice 14:
- admin_web dentro de Mini App Cliente
- business_intake que cree negocio approved automaticamente
- support_ticket que cambie order.status sin disputa formal

## Observability enums - slice 24

`observability_mode`:

- `disabled`
- `local_only`
- `persisted`
- `logs_only`

`observability_event_type`:

- `view_changed`
- `action_clicked`
- `form_submitted`
- `api_request_started`
- `api_request_completed`
- `api_request_failed`
- `auth_refresh_started`
- `auth_refresh_completed`
- `auth_refresh_failed`
- `offline`
- `online`
- `visible_error_shown`
- `critical_operation_started`
- `critical_operation_completed`
- `critical_operation_failed`
- `backend_request_completed`
- `backend_request_failed`
- `storage_failure`
- `cache_failure`
- `db_pool_saturation`
- `rate_limit_triggered`
- `idempotency_conflict`
- `webhook_received`
- `watcher_step_failed`

`observability_severity`:

- `debug`
- `info`
- `warn`
- `error`
