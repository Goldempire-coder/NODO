# STATE_CONTRACT.md

## business_intake.status

- draft
- submitted
- accepted
- rejected

## Transiciones

- `draft -> submitted`: bot completa datos minimos y crea solicitud para revision.
- `submitted -> accepted`: admin/super_admin acepta con reason en Admin Web.
- `submitted -> rejected`: admin/super_admin rechaza con reason en Admin Web.

## Estado conversacional

- `last_step` no es estado de aprobacion; solo representa el paso del formulario.
- `last_update_id` controla idempotencia del ultimo update procesado.
- Repetir un update no cambia estados ni duplica side effects.

## Post-MVP

- Video/documentos de video.
- Estados `under_review` y `archived` como activos de operacion.
