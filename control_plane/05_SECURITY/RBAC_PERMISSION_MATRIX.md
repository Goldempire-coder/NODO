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
| remitter | create_support_ticket | support_ticket | own scope/order when applicable | support_ticket_created | yes |
| business_owner | create_support_ticket | support_ticket | own business/order when applicable | support_ticket_created | yes |
| remitter | create_support_message | own ticket | ticket open/waiting_user/waiting_support | support_message_created | yes |
| business_owner | create_support_message | own business ticket | ticket open/waiting_business/waiting_support | support_message_created | yes |
| support | create_support_message | support ticket | support active | support_message_created | yes |
| admin | create_support_message | support ticket | admin active | support_message_created | yes |
| super_admin | create_support_message | support ticket | super_admin active | support_message_created | yes |
| support | escalate_support_ticket | support ticket | support active, reason required | support_ticket_escalated | yes |
| admin | escalate_support_ticket | support ticket | admin active, reason required | support_ticket_escalated | yes |
| super_admin | escalate_support_ticket | support ticket | super_admin active, reason required | support_ticket_escalated | yes |
| support | resolve_support_ticket | support ticket | support active, reason required | support_ticket_resolved | yes |
| admin | resolve_support_ticket | support ticket | admin active, reason required | support_ticket_resolved | yes |
| super_admin | resolve_support_ticket | support ticket | super_admin active, reason required | support_ticket_resolved | yes |

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
| remitter | open_dispute | own order | payment_reported/payment_confirmed/delivered | dispute_opened | yes |
| remitter | view_order_messages | own order | payment_reported/payment_rejected/payment_confirmed/delivered/disputed | no | yes |
| remitter | create_order_message | own order | payment_reported/payment_rejected/payment_confirmed/delivered/disputed | message_created/dispute_message_created | yes |
| remitter | upload_message_attachment | own order | payment_reported/payment_rejected/payment_confirmed/delivered/disputed | message_attachment_uploaded | yes |
| remitter | rate_business | own completed order | completed, not previously rated | rating_created | yes |
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
| business_owner | reject_payment_report | own business order | payment_reported + payment_report submitted + approved business + reason required | payment_report_rejected | yes |
| business_owner | mark_delivered | own business order | payment_confirmed + approved business | order_delivered | yes |
| business_owner | respond_dispute | own order/dispute | dispute open | dispute_message_created | yes |
| business_owner | view_order_messages | own business order | payment_reported/payment_rejected/payment_confirmed/delivered/disputed + approved business | no | yes |
| business_owner | create_order_message | own business order | payment_reported/payment_rejected/payment_confirmed/delivered/disputed + approved business | message_created/dispute_message_created | yes |
| business_owner | upload_message_attachment | own business order | payment_reported/payment_rejected/payment_confirmed/delivered/disputed + approved business | message_attachment_uploaded | yes |
| business_owner | buy_credits_stripe | own business | approved | credit_checkout_created | yes |
| business_owner | submit_manual_credit_payment | own business | approved | manual_credit_payment_submitted | yes |
| business_owner | view_credit_wallet | own business wallet | approved business | no | yes |
| business_owner | view_credit_ledger | own business wallet | approved business | no | yes |
| business_owner | view_referrals | own business | approved business | no | yes |
| business_owner | apply_referral_code | own business | approved business, no self-referral, not previously used | referral_applied | yes |
| business_operator | confirm_payment | assigned business | approved, operator active | payment_confirmed | post-MVP |
| business_operator | reject_payment_report | assigned business | approved, operator active | payment_report_rejected | post-MVP |
| business_operator | mark_delivered | assigned business | approved, operator active | order_delivered | post-MVP |
| business_operator | adjust_credits | business | any | no | no |

## Business access links

| Actor | Accion | Recurso | Estado requerido | Audit | Permitido |
| --- | --- | --- | --- | --- | --- |
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
| admin | adjust_credits | business wallet | any | credit_adjusted_by_admin | yes |
| admin | view_credit_purchases | credit purchases | admin active | no | yes |
| admin | view_credit_purchase_detail | credit purchase | admin active | no | yes |
| super_admin | approve_manual_credit_payment | credit purchase | pending_manual_review | manual_credit_payment_approved | yes |
| super_admin | reject_manual_credit_payment | credit purchase | pending_manual_review | manual_credit_payment_rejected | yes |
| super_admin | adjust_credits | business wallet | any, reason required | credit_adjusted_by_admin | yes |
| super_admin | view_credit_purchases | credit purchases | super_admin active | no | yes |
| super_admin | view_credit_purchase_detail | credit purchase | super_admin active | no | yes |
| support | view_credit_purchases | credit purchases | support active | no | yes |
| support | view_credit_purchase_detail | credit purchase | support active, masked proof metadata only | no | yes |
| support | approve_manual_credit_payment | credit purchase | any | no | no |
| support | reject_manual_credit_payment | credit purchase | any | no | no |
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

## Reglas obligatorias

- Todo permiso mutante debe validar actor, ownership, estado actual y transicion permitida.
- Toda accion admin sensible requiere reason.
- Las decisiones admin deben quedar en audit log.
- El frontend no decide permisos; solo refleja lo que la API autoriza.
- Si falta una fila para una accion nueva, la accion esta prohibida.
- En `slice_07_chat_disputes`, admin/super_admin/support solo pueden ver disputas segun las filas de lectura.
- `resolve_dispute` queda prohibido en slice 07.
- En `slice_09_admin_console`, `admin` y `super_admin` pueden resolver disputas usando el contrato de `DISPUTES_API.md`; `support` sigue read-only.
