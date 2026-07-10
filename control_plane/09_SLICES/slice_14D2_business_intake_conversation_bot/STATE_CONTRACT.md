# STATE_CONTRACT.md

## Intake status

- `draft`
- `submitted`
- `accepted`
- `rejected`

## last_step

Valores canonicos:
- `start`
- `awaiting_referral_code`
- `awaiting_whatsapp_phone`
- `awaiting_business_name`
- `awaiting_responsible_name`
- `awaiting_city`
- `awaiting_business_phone`
- `awaiting_operation`
- `awaiting_banks`
- `awaiting_methods`
- `awaiting_min_amount`
- `awaiting_max_amount`
- `awaiting_schedule`
- `awaiting_references`
- `awaiting_documents`
- `submitted`

Transiciones:
- `start -> awaiting_referral_code`
- `awaiting_referral_code -> awaiting_whatsapp_phone`
- `awaiting_whatsapp_phone -> awaiting_documents`
- Legacy/internal only: `awaiting_contact -> awaiting_business_name`
- `awaiting_business_name -> awaiting_responsible_name`
- `awaiting_responsible_name -> awaiting_city`
- `awaiting_city -> awaiting_business_phone`
- `awaiting_business_phone -> awaiting_operation`
- `awaiting_operation -> awaiting_banks`
- `awaiting_banks -> awaiting_methods`
- `awaiting_methods -> awaiting_min_amount`
- `awaiting_min_amount -> awaiting_max_amount`
- `awaiting_max_amount -> awaiting_schedule`
- `awaiting_schedule -> awaiting_references`
- `awaiting_references -> awaiting_documents`
- `awaiting_documents -> submitted`

Invalid input:
- No avanza paso.
- Mantiene `status = draft`.
- Webhook devuelve `200 OK` y envia mensaje correctivo al chat para evitar retries de Telegram.

Final:
- `submitted` solo por confirmacion final.
- `accepted` y `rejected` solo por admin.
