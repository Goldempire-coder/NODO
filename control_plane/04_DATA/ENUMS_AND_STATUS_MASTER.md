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

user.status:
- active
- restricted
- blocked
- dormant

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

business.risk_level:
- normal
- watch
- under_review
- restricted
- high_risk

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

Regla slice_06:
- `payment_rejected` es estado persistente canonico cuando el negocio rechaza un reporte de pago.
- `payment_rejected` no debe devolverse automaticamente a `waiting_payment`.

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
- business_confirmed_payment_but_not_delivered
- payment_mobile_not_received
- amount_incorrect
- wrong_receiver_data
- other

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
- `submitted -> rejected` cuando el negocio rechaza reporte de pago.
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

credit_purchase.status:
- created
- pending_payment
- pending_manual_review
- paid
- approved
- rejected
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
- waiting_business
- waiting_support
- escalated
- linked_to_dispute
- resolved
- closed

support_ticket.scope:
- client_general
- order_support
- business_general
- admin_internal

support_message.visibility:
- participants
- support_internal
- admin_internal

support_event.type:
- support_ticket_created
- support_message_created
- support_ticket_escalated
- support_ticket_linked_to_dispute
- support_ticket_resolved
- support_ticket_closed

Prohibidos slice 14:
- admin_web dentro de Mini App Cliente
- business_intake que cree negocio approved automaticamente
- support_ticket que cambie order.status sin disputa formal

