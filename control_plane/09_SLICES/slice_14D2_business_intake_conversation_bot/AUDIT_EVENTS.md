# AUDIT_EVENTS.md

Eventos requeridos:
- `business_intake_started`
- `business_intake_step_answered`
- `business_intake_document_uploaded`
- `business_intake_submitted`

Eventos admin heredados de 14D:
- `business_intake_viewed_by_admin`
- `business_intake_accepted`
- `business_intake_rejected`
- `business_intake_deleted`

Reglas:
- No incluir token, `storage_path`, documentos completos ni telefonos completos en metadata.
- Update repetido no duplica audit.
