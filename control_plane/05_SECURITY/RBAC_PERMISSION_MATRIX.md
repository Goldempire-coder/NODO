# RBAC_PERMISSION_MATRIX.md

Formato: actor | accion | recurso | estado requerido | audit | permitido.

## Roles oficiales

- guest: sin sesion valida.
- remitter: usuario que busca negocios y crea ordenes.
- business_owner: duenio de negocio.
- admin: operador interno con permisos altos.
- super_admin: owner/sistema con permisos criticos.
- support: soporte MVP con permisos definidos por admin.

Post-MVP:

- business_operator: operador autorizado por negocio.
- support_readonly: soporte solo lectura.

## Auth y perfil

| Actor | Accion | Recurso | Estado requerido | Audit | Permitido |
| --- | --- | --- | --- | --- | --- |
| guest | auth_telegram | auth | valid Telegram initData | user_created/user_login/auth_failed | yes |
| remitter | refresh_session | own session | user active/restricted, session active | session_refreshed | yes |
| business_owner | refresh_session | own session | user active/restricted, session active | session_refreshed | yes |
| admin | refresh_session | own session | user active, session active | session_refreshed | yes |
| super_admin | refresh_session | own session | user active, session active | session_refreshed | yes |
| support | refresh_session | own session | user active, session active | session_refreshed | yes |
| remitter | logout | own session | authenticated | user_logout | yes |
| business_owner | logout | own session | authenticated | user_logout | yes |
| admin | logout | own session | authenticated | user_logout | yes |
| super_admin | logout | own session | authenticated | user_logout | yes |
| support | logout | own session | authenticated | user_logout | yes |
| remitter | view_own_profile | own user | authenticated | no | yes |
| business_owner | view_own_profile | own user | authenticated | no | yes |
| admin | view_own_profile | own user | authenticated | no | yes |
| super_admin | view_own_profile | own user | authenticated | no | yes |
| support | view_own_profile | own user | authenticated | no | yes |
| guest | view_own_profile | user | none | no | no |

## Surface access

| Actor | Accion | Recurso | Estado requerido | Audit | Permitido |
| --- | --- | --- | --- | --- | --- |
| remitter | access_client_mini_app | client_mini_app | user active | no | yes |
| business_owner | access_client_mini_app | client_mini_app | user active | no | yes |
| business_owner | access_business_mini_app | business_mini_app | user active, own business approved, `business_access_links.status = active`, Telegram initData matches linked user | surface_access_denied on failure | yes |
| remitter | access_business_mini_app | business_mini_app | any | surface_access_denied | no |
| admin | access_admin_web | admin_web | admin active | no | yes |
| super_admin | access_admin_web | admin_web | super_admin active | no | yes |
| support | access_admin_web | admin_web | support active | no | yes |
| business_owner | access_admin_web | admin_web | any | surface_access_denied | no |
| guest | access_authenticated_surface | any | unauthenticated | surface_access_denied | no |

## Business intake

| Actor | Accion | Recurso | Estado requerido | Audit | Permitido |
| --- | --- | --- | --- | --- | --- |
| guest | start_business_intake | business_intake | bot webhook valid, contact pending | business_intake_started | yes |
| guest | submit_business_intake | own intake | draft, contact shared | business_intake_submitted | yes |
| guest | upload_business_intake_document | own intake | draft/submitted | business_intake_document_uploaded | yes |
| admin | view_business_intake | business_intake | admin active | business_intake_viewed_by_admin | yes |
| super_admin | view_business_intake | business_intake | super_admin active | business_intake_viewed_by_admin | yes |
| support | view_business_intake | business_intake | support active, masked | no | yes |
| admin | accept_business_intake | submitted/under_review intake | admin active, reason required | business_intake_accepted | yes |
| super_admin | accept_business_intake | submitted/under_review intake | super_admin active, reason required | business_intake_accepted | yes |
| support | accept_business_intake | business_intake | any | no | no |
| admin | reject_business_intake | submitted/under_review intake | admin active, reason required | business_intake_rejected | yes |
| super_admin | reject_business_intake | submitted/under_review intake | super_admin active, reason required | business_intake_rejected | yes |
| support | reject_business_intake | business_intake | any | no | no |

## Support tickets

| Actor | Accion | Recurso | Estado requerido | Audit | Permitido |
| --- | --- | --- | --- | --- | --- |
| remitter | create_support_ticket | support_ticket | own client_general/client_order scope | support_ticket_created | yes |
| business_owner | create_support_ticket | support_ticket | own business_general/business_order/business_ad/business_credit scope | support_ticket_created | yes |
| remitter | view_support_ticket_detail | own ticket | own requester_user_id or own order | no | yes |
| business_owner | view_support_ticket_detail | own business ticket | own business/order/ad/credit_purchase | no | yes |
| remitter | create_support_message | own ticket | ticket open/waiting_user/waiting_support/escalated | support_message_created | yes |
| business_owner | create_support_message | own business ticket | ticket open/waiting_user/waiting_support/escalated | support_message_created | yes |
| remitter | upload_support_attachment | own ticket/message | MIME allowed, max 5 MB, ticket open/waiting_user/waiting_support/escalated | support_attachment_uploaded | yes |
| business_owner | upload_support_attachment | own business ticket/message | MIME allowed, max 5 MB, own business resource | support_attachment_uploaded | yes |
| remitter | close_support_ticket | own ticket | ticket open/waiting_user/waiting_support/escalated | support_ticket_closed | yes |
| business_owner | close_support_ticket | own business ticket | ticket open/waiting_user/waiting_support/escalated, active business access | support_ticket_closed | yes |
| support | view_support_ticket_detail | support ticket | support active, masked where required | no | yes |
| admin | view_support_ticket_detail | support ticket | admin active | no | yes |
| super_admin | view_support_ticket_detail | support ticket | super_admin active | no | yes |
| support | create_support_message | support ticket | support active, ticket open/waiting_user/waiting_support/escalated | support_message_created | yes |
| admin | create_support_message | support ticket | admin active, ticket open/waiting_user/waiting_support/escalated | support_message_created | yes |
| super_admin | create_support_message | support ticket | super_admin active, ticket open/waiting_user/waiting_support/escalated | support_message_created | yes |
| support | assign_support_ticket | support ticket | support active, ticket active, assignee support/admin/super_admin, reason required | support_ticket_assigned | yes |
| admin | assign_support_ticket | support ticket | admin active, ticket active, assignee support/admin/super_admin, reason required | support_ticket_assigned | yes |
| super_admin | assign_support_ticket | support ticket | super_admin active, ticket active, assignee support/admin/super_admin, reason required | support_ticket_assigned | yes |
| support | escalate_support_ticket | support ticket | support active, reason required | support_ticket_escalated | yes |
| admin | escalate_support_ticket | support ticket | admin active, reason required | support_ticket_escalated | yes |
| super_admin | escalate_support_ticket | support ticket | super_admin active, reason required | support_ticket_escalated | yes |
| support | resolve_support_ticket | support ticket | support active, reason required | support_ticket_resolved | yes |
| admin | resolve_support_ticket | support ticket | admin active, reason required | support_ticket_resolved | yes |
| super_admin | resolve_support_ticket | support ticket | super_admin active, reason required | support_ticket_resolved | yes |
| support | close_support_ticket | support ticket | forbidden; support may resolve but cannot close definitively | no | no |
| admin | close_support_ticket | support ticket | admin active, ticket resolved, reason required | support_ticket_closed | yes |
| super_admin | close_support_ticket | support ticket | super_admin active, ticket resolved, reason required | support_ticket_closed | yes |
| support | view_support_attachment | support attachment | support active, ticket visible, signed URL short-lived | support_attachment_viewed | yes |
| admin | view_support_attachment | support attachment | admin active, ticket visible, signed URL short-lived | support_attachment_viewed | yes |
| super_admin | view_support_attachment | support attachment | super_admin active, ticket visible, signed URL short-lived | support_attachment_viewed | yes |
| support | create_formal_dispute_from_support | dispute | any | no | no |
| support | change_order_from_support | order | any | no | no |
| support | change_credit_from_support | credit_wallet/credit_purchase | any | no | no |
| support | change_ad_from_support | ad | any | no | no |
| support | change_user_or_business_access_from_support | user/business_access_link | any | no | no |

## Remitente

| Actor | Accion | Recurso | Estado requerido | Audit | Permitido |
| --- | --- | --- | --- | --- | --- |
| remitter | view_marketplace | active ads | user active | no | yes |
| remitter | view_business_detail | active business/ad | user active | no | yes |
| remitter | create_order | active ad | user active, business approved, ad active | order_created | yes |
| remitter | view_own_order | own order | authenticated, own order | no | yes |
| remitter | extend_payment_deadline | own order | waiting_payment, extension_used=false | payment_deadline_extended | yes |
| remitter | report_payment | own order | waiting_payment | payment_reported | yes |
| remitter | upload_payment_evidence | own order | waiting_payment/payment_reported | payment_evidence_uploaded | yes |
| remitter | view_payment_instructions | own order | waiting_payment and not expired | payment_instructions_viewed | yes |
| remitter | confirm_received | own order | delivered | order_completed | yes |
| remitter | open_dispute | own order | payment_reported/payment_rejected/payment_confirmed/delivered | dispute_opened | yes |
| remitter | view_order_messages | own order | waiting_payment/payment_reported/payment_rejected/payment_confirmed/delivered/disputed | no | yes |
| remitter | create_order_message | own order | waiting_payment/payment_reported/payment_rejected/payment_confirmed/delivered/disputed | message_created/dispute_message_created | yes |
| remitter | upload_message_attachment | own order | waiting_payment/payment_reported/payment_rejected/payment_confirmed/delivered/disputed | message_attachment_uploaded | yes |
| remitter | share_receiver_details | own order | payment_confirmed | order_receiver_details_shared without values | yes |
| remitter | view_receiver_details | own order | payment_confirmed/delivered/disputed | order_receiver_details_viewed without values | yes |
| remitter | rate_business | own completed order | completed with manual_confirmed/auto_completed_after_24h, or admin_resolved with dispute closed; not previously rated | rating_created | yes |
| remitter | cancel_order | own order | waiting_payment before payment report | order_cancelled | yes |
| remitter | modify_rate_snapshot | own order | any | no | no |

## Negocio

| Actor | Accion | Recurso | Estado requerido | Audit | Permitido |
| --- | --- | --- | --- | --- | --- |
| guest | create_business | business | none | no | no |
| guest | view_business_verification | business | none | no | no |
| business_owner | create_business | own business | legacy/internal, not Mini App Negocio self-onboarding | business_created | no |
| business_owner | update_business_profile | own business | approved/suspended own business, active business access link, fields allowed only | business_updated | yes |
| business_owner | upload_verification_document | own business | legacy/not Mini App Negocio; active flow is Bot Intake/Admin Web | verification_document_uploaded | no |
| business_owner | submit_verification | own business | legacy/not Mini App Negocio; active flow is Bot Intake/Admin Web | business_submitted | no |
| business_owner | view_own_payment_methods | own approved business payment methods | approved business, owner, active business access link | no | yes |
| business_owner | create_ad | own business | approved, credits/founder access valid | ad_created | yes |
| business_owner | view_own_ads | own business ads | approved business, owner | no | yes |
| business_owner | update_ad | own ad | active/paused and not expired | ad_updated | yes |
| business_owner | pause_ad | own ad | active | ad_paused | yes |
| business_owner | archive_ad | own ad | paused/expired | ad_archived | yes |
| business_owner | view_incoming_orders | own business | approved | no | yes |
| business_owner | confirm_payment | own business order | payment_reported + payment_report submitted + approved business | payment_confirmed/credits_consumed | yes |
| business_owner | reject_payment_report | own business order | legacy route only; new calls return PAYMENT_REJECTION_NOT_ALLOWED | no mutation | no |
| business_owner | mark_delivered | own business order | payment_confirmed + approved business | order_delivered | yes |
| business_owner | open_dispute | own business order | payment_reported/payment_rejected legacy/payment_confirmed/delivered + approved business; payment problem uses structured reason | dispute_opened | yes |
| business_owner | respond_dispute | own order/dispute | dispute open | dispute_message_created | yes |
| business_owner | view_order_messages | own business order | waiting_payment/payment_reported/payment_rejected/payment_confirmed/delivered/disputed + approved business | no | yes |
| business_owner | create_order_message | own business order | waiting_payment/payment_reported/payment_rejected/payment_confirmed/delivered/disputed + approved business | message_created/dispute_message_created | yes |
| business_owner | upload_message_attachment | own business order | waiting_payment/payment_reported/payment_rejected/payment_confirmed/delivered/disputed + approved business | message_attachment_uploaded | yes |
| business_owner | view_receiver_details | own business order | payment_confirmed/delivered/disputed + approved business | order_receiver_details_viewed without values | yes |
| business_owner | buy_credits_stripe | own business | approved | credit_checkout_created | yes |
| business_owner | buy_credits_base_usdc | own business | approved, active business access link | onchain_credit_purchase_created | yes |
| business_owner | submit_onchain_credit_tx_hash | own credit purchase | approved, active business access link, purchase own and non-terminal | onchain_tx_hash_submitted | yes |
| business_owner | submit_manual_credit_payment | own business | approved | manual_credit_payment_submitted | yes |
| business_owner | view_credit_wallet | own business wallet | approved business | no | yes |
| business_owner | view_credit_ledger | own business wallet | approved business | no | yes |
| business_owner | view_referrals | own business | approved business | no | yes |
| business_owner | apply_referral_code | own business | approved business, no self-referral, not previously used | referral_applied | yes |
| business_operator | confirm_payment | assigned business | approved, operator active | payment_confirmed | post-MVP |
| business_operator | reject_payment_report | assigned business | legacy route prohibited for new transitions | no mutation | no |
| business_operator | mark_delivered | assigned business | approved, operator active | order_delivered | post-MVP |
| business_operator | adjust_credits | business | any | no | no |

## Order chat and sensitive receiver evidence

| Actor | Accion | Recurso | Estado requerido | Audit | Permitido |
| --- | --- | --- | --- | --- | --- |
| admin | view_waiting_payment_message_body_via_general_messages | order messages | waiting_payment | no | no |
| super_admin | view_waiting_payment_message_body_via_general_messages | order messages | waiting_payment | no | no |
| support | view_waiting_payment_message_body_via_general_messages | order messages | waiting_payment | no | no |
| admin | view_full_receiver_details_via_general_order_or_messages | order/receiver details | any | no | no |
| super_admin | view_full_receiver_details_via_general_order_or_messages | order/receiver details | any | no | no |
| support | view_full_receiver_details_via_general_order_or_messages | order/receiver details | any | no | no |

Admin/support evidence access must use a separately contracted purpose-bound
viewer with explicit permission, reason and audit. This matrix does not grant
that future reveal.

## Business access links

| Actor | Accion | Recurso | Estado requerido | Audit | Permitido |
| --- | --- | --- | --- | --- | --- |
| admin | view_business_access_links | business_access_link | admin active | no | yes |
| super_admin | view_business_access_links | business_access_link | super_admin active | no | yes |
| support | view_business_access_links | business_access_link | support active, masked/read-only | no | yes |
| admin | link_business_user | business_access_link | admin active, business approved or pending with explicit reason, Telegram user known | business_access_linked | yes |
| super_admin | link_business_user | business_access_link | super_admin active, business approved or pending with explicit reason, Telegram user known | business_access_linked | yes |
| support | link_business_user | business_access_link | any | no | no |
| admin | unlink_business_user | business_access_link | admin active, reason required | business_access_unlinked | yes |
| super_admin | unlink_business_user | business_access_link | super_admin active, reason required | business_access_unlinked | yes |
| admin | suspend_business_access | business_access_link | active link, reason required | business_access_suspended | yes |
| super_admin | suspend_business_access | business_access_link | active link, reason required | business_access_suspended | yes |
| admin | reactivate_business_access | business_access_link | suspended link, reason required, business approved, user active | business_access_reactivated | yes |
| super_admin | reactivate_business_access | business_access_link | suspended link, reason required, business approved, user active | business_access_reactivated | yes |
| admin | block_business_access | business_access_link | active/suspended link, reason required | business_access_blocked | yes |
| super_admin | block_business_access | business_access_link | active/suspended link, reason required | business_access_blocked | yes |

## Admin

| Actor | Accion | Recurso | Estado requerido | Audit | Permitido |
| --- | --- | --- | --- | --- | --- |
| admin | view_admin_dashboard | system | admin active | admin_viewed_dashboard | yes |
| admin | view_admin_users | users | admin active | admin_user_list_viewed | yes |
| super_admin | view_admin_users | users | super_admin active | admin_user_list_viewed | yes |
| support | view_admin_users | users | support active, masked/read-only | no | yes |
| admin | view_admin_user_detail | user | admin active | admin_user_detail_viewed | yes |
| super_admin | view_admin_user_detail | user | super_admin active | admin_user_detail_viewed | yes |
| support | view_admin_user_detail | user | support active, masked/read-only | no | yes |
| admin | suspend_user | user | active user, reason required, cannot mutate admin/super_admin | user_suspended | yes |
| super_admin | suspend_user | user | active user, reason required, cannot suspend last active super_admin | user_suspended | yes |
| support | suspend_user | user | any | no | no |
| admin | reactivate_user | user | restricted/dormant user, reason required, cannot mutate admin/super_admin | user_reactivated | yes |
| super_admin | reactivate_user | user | restricted/dormant user, reason required | user_reactivated | yes |
| support | reactivate_user | user | any | no | no |
| admin | block_user | user | active/restricted/dormant user, reason required, cannot mutate admin/super_admin | user_blocked | yes |
| super_admin | block_user | user | active/restricted/dormant user, reason required, cannot block last active super_admin | user_blocked | yes |
| support | block_user | user | any | no | no |
| admin | view_pending_businesses | businesses | admin active | no | yes |
| super_admin | view_pending_businesses | businesses | super_admin active | no | yes |
| support | view_pending_businesses | businesses | support active | no | yes |
| admin | view_business_verification_detail | pending/rejected/approved business | admin active | verification_document_viewed when document opened | yes |
| super_admin | view_business_verification_detail | pending/rejected/approved business | super_admin active | verification_document_viewed when document opened | yes |
| support | view_business_verification_detail | pending/rejected/approved business | support active | no document full view by default | yes |
| admin | approve_business | pending business | admin active, business pending, reason required | business_approved | yes |
| super_admin | approve_business | pending business | super_admin active, business pending, reason required | business_approved | yes |
| support | approve_business | pending business | any | no | no |
| admin | reject_business | pending business | admin active, business pending, reason required | business_rejected | yes |
| super_admin | reject_business | pending business | super_admin active, business pending, reason required | business_rejected | yes |
| support | reject_business | pending business | any | no | no |
| admin | suspend_business | approved business | approved, reason required | business_suspended | yes |
| super_admin | suspend_business | approved business | approved, reason required | business_suspended | yes |
| admin | reactivate_business | suspended business | suspended, reason required | business_reactivated | yes |
| super_admin | reactivate_business | suspended business | suspended, reason required | business_reactivated | yes |
| admin | block_business | approved/suspended business | reason required | business_blocked | yes |
| super_admin | block_business | approved/suspended business | reason required | business_blocked | yes |
| support | suspend_business | business | any | no | no |
| support | reactivate_business | business | any | no | no |
| support | block_business | business | any | no | no |
| admin | approve_manual_credit_payment | credit purchase | pending_manual_review | manual_credit_payment_approved | yes |
| admin | reject_manual_credit_payment | credit purchase | pending_manual_review | manual_credit_payment_rejected | yes |
| admin | reject_onchain_credit_payment | credit purchase | under_review, reason required | onchain_payment_rejected | yes |
| admin | adjust_credits | business wallet | any | credit_adjusted_by_admin | yes |
| admin | view_credit_purchases | credit purchases | admin active | no | yes |
| admin | view_credit_purchase_detail | credit purchase | admin active | no | yes |
| super_admin | approve_manual_credit_payment | credit purchase | pending_manual_review | manual_credit_payment_approved | yes |
| super_admin | reject_manual_credit_payment | credit purchase | pending_manual_review | manual_credit_payment_rejected | yes |
| super_admin | reject_onchain_credit_payment | credit purchase | under_review, reason required | onchain_payment_rejected | yes |
| super_admin | adjust_credits | business wallet | any, reason required | credit_adjusted_by_admin | yes |
| super_admin | view_credit_purchases | credit purchases | super_admin active | no | yes |
| super_admin | view_credit_purchase_detail | credit purchase | super_admin active | no | yes |
| support | view_credit_purchases | credit purchases | support active | no | yes |
| support | view_credit_purchase_detail | credit purchase | support active, masked proof metadata only | no | yes |
| support | approve_manual_credit_payment | credit purchase | any | no | no |
| support | reject_manual_credit_payment | credit purchase | any | no | no |
| support | reject_onchain_credit_payment | credit purchase | any | no | no |
| support | adjust_credits | business wallet | any | no | no |
| admin | view_disputes | disputes | admin active | no | yes |
| admin | view_dispute_detail | dispute | admin active | no | yes |
| super_admin | view_disputes | disputes | super_admin active | no | yes |
| super_admin | view_dispute_detail | dispute | super_admin active | no | yes |
| admin | resolve_dispute | dispute | slice_09, dispute open/in_review, reason required | dispute_resolved | yes |
| super_admin | resolve_dispute | dispute | slice_09, dispute open/in_review, reason required | dispute_resolved | yes |
| admin | view_audit_logs | audit logs | admin active | audit_logs_viewed | yes |
| admin | view_job_runs | job_runs | admin active | no | yes |
| super_admin | view_job_runs | job_runs | super_admin active | no | yes |
| support | view_job_runs | job_runs | support active | no | yes |
| admin | dry_run_expire_and_escalate_orders | jobs | admin active, dry_run only | job_started/job_finished/job_failed when recorded | yes |
| super_admin | dry_run_expire_and_escalate_orders | jobs | super_admin active, dry_run only | job_started/job_finished/job_failed when recorded | yes |
| support | dry_run_expire_and_escalate_orders | jobs | any | no | no |
| admin | export_sensitive_data | system | any | sensitive_export_requested | no by default |
| super_admin | manage_admin_roles | admin users | active | admin_role_changed | yes |

## Soporte MVP y soporte solo lectura post-MVP

| Actor | Accion | Recurso | Estado requerido | Audit | Permitido |
| --- | --- | --- | --- | --- | --- |
| support | view_orders | orders | support active | no | yes |
| support | view_businesses | businesses | support active | no | yes |
| support | view_disputes | disputes | support active | no | yes |
| support | view_dispute_detail | dispute | support active | no | yes |
| support | resolve_dispute | dispute | any | no | no |
| support_readonly | view_orders | orders | support active | no | post-MVP |
| support_readonly | view_businesses | businesses | support active | no | post-MVP |
| support_readonly | view_disputes | disputes | support active | no | post-MVP |
| support_readonly | approve_business | business | any | no | no |
| support_readonly | adjust_credits | wallet | any | no | no |
| support_readonly | resolve_dispute | dispute | any | no | no |

## Staff interno 20C

`users.role` sigue siendo rol base. La granularidad de empleados usa `staff_profiles.staff_role` y `staff_permissions`.

| Actor staff | Accion | Recurso | Estado requerido | Audit | Permitido |
| --- | --- | --- | --- | --- | --- |
| support_agent | view_assigned_support_tickets | support_ticket | user active, staff active, permission active, assigned_only | no | yes |
| support_agent | reply_support_ticket | support_ticket | ticket assigned or permitted queue, permission active | support_message_created | yes |
| support_agent | view_support_attachment | support_attachment | permission active, reason required | support_attachment_viewed | yes |
| support_agent | view_support_queue | support_ticket | permission active, queue/category scope | no | yes when granted |
| support_lead | view_support_queue | support_ticket | user active, staff active, permission active | no | yes |
| support_lead | assign_support_ticket | support_ticket | permission active, reason required | staff_ticket_assigned | yes |
| support_lead | escalate_support_ticket | support_ticket | permission active, reason required | support_ticket_escalated | yes |
| support_lead | resolve_support_ticket | support_ticket | permission active, reason required | support_ticket_resolved | yes |
| support_lead | close_support_ticket | support_ticket | forbidden; definitive close requires admin or super_admin base role | no | no |
| operations_readonly | view_users_masked | users | permission active | no | yes |
| operations_readonly | view_businesses_masked | businesses | permission active | no | yes |
| operations_readonly | view_orders_masked | orders | permission active | no | yes |
| operations_readonly | view_audit_limited | audit_logs | permission active | staff_activity_viewed | yes |
| operations_readonly | view_metrics_limited | metrics | permission active | no | yes |
| support_agent | block_user | users | any | no | no |
| support_agent | suspend_user | users | any | no | no |
| support_agent | change_user_role | users | any | no | no |
| support_agent | mutate_business_access_links | business_access_links | any | no | no |
| support_agent | approve_business | businesses | any | no | no |
| support_agent | approve_credit_payment | credit_purchases | any | no | no |
| support_agent | manual_credit_adjustment | credit_wallets | any | no | no |
| support_agent | resolve_dispute | disputes | any | no | no |
| support_agent | mutate_orders | orders | any | no | no |
| support_agent | mutate_ads | ads | any | no | no |
| support_agent | mutate_credits | credits | any | no | no |
| support_lead | block_user | users | any | no | no |
| support_lead | mutate_business_access_links | business_access_links | any | no | no |
| support_lead | approve_credit_payment | credit_purchases | any | no | no |
| support_lead | resolve_dispute | disputes | any | no | no |
| operations_readonly | any_mutation | any | any | no | no |
| super_admin | manage_staff_profiles | staff | user active, reason/idempotency required | staff_activated/staff_suspended/staff_revoked | yes |
| super_admin | manage_staff_permissions | staff_permissions | reason/idempotency required | staff_permissions_updated | yes |
| admin | view_staff_profiles | staff | admin active | no | yes when granted |
| admin | manage_staff_permissions | staff_permissions | any | no | no |

## Reglas obligatorias

- Todo permiso mutante debe validar actor, ownership, estado actual y transicion permitida.
- Toda accion admin sensible requiere reason.
- Las decisiones admin deben quedar en audit log.
- El frontend no decide permisos; solo refleja lo que la API autoriza.
- Si falta una fila para una accion nueva, la accion esta prohibida.
- En `slice_07_chat_disputes`, admin/super_admin/support solo pueden ver disputas segun las filas de lectura.
- `resolve_dispute` queda prohibido en slice 07.
- En `slice_09_admin_console`, `admin` y `super_admin` pueden resolver disputas usando el contrato de `DISPUTES_API.md`; `support` sigue read-only.

## Slice 42D0 - holds de publicacion

| Actor | Accion | Recurso | Estado requerido | Audit | Permitido |
| --- | --- | --- | --- | --- | --- |
| remitter | create_structured_operation_report | own order | estado reportable, ownership, rate limit, idempotencia | structured_operation_report_created | yes |
| business_owner | create_structured_operation_report | order | any | no | no |
| support | release_business_publication_hold | hold | rol base sin permiso staff explicito | no | no |
| support_agent/support_lead | release_business_publication_hold | hold | user/staff active, permiso explicito; ticket cumple assigned_only, queue_scope o category_scope; reason e idempotencia | business_publication_hold_released | yes when granted |
| admin | release_business_publication_hold | hold | admin active, hold active, reason, idempotencia | business_publication_hold_released | yes |
| super_admin | release_business_publication_hold | hold | super_admin active, hold active, reason, idempotencia | business_publication_hold_released | yes |

Cerrar o resolver un ticket no implica `release_business_publication_hold`. Si
el permiso no existe o esta inactivo, la liberacion queda prohibida.
