# BUSINESS_INTAKE_LIFECYCLE.md

## Estados

- `draft`
- `submitted`
- `accepted`
- `rejected`

Estados post-MVP/legacy, no activos para slice 14D:

- `under_review`
- `archived`

## Transiciones

- `draft -> submitted`: bot completa datos minimos.
- `submitted -> accepted`: admin/super_admin acepta con reason.
- `submitted -> rejected`: admin/super_admin rechaza con reason.

## Pasos conversacionales canonicos

`business_intake_requests.last_step` debe usar solo estos valores activos:

- `start`
- `awaiting_contact`
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

Reglas de avance:
- `/start` crea o recupera un draft y deja `last_step = awaiting_contact`.
- Cada respuesta valida se persiste inmediatamente y avanza al siguiente paso.
- Respuesta invalida no avanza `last_step`; devuelve error/copy seguro y mantiene el draft.
- `awaiting_documents` permite recibir cero o mas documentos permitidos y luego confirmar envio.
- La confirmacion final cambia `status = submitted` y `last_step = submitted`.
- Cuando `status in ('submitted', 'accepted', 'rejected')`, nuevos mensajes no deben modificar datos del intake salvo contrato futuro explicito.

## Reglas

- `accepted` no crea automaticamente negocio activo.
- Crear negocio desde intake requiere accion admin explicita.
- Asociar Telegram ID requiere accion admin explicita.
- Activar acceso a Mini App Negocio requiere negocio `approved` y `business_access_links.status = active`.
- El bot no autoriza acceso; solo notifica/apunta a la superficie despues de decision admin/backend.
- Rechazo requiere `admin_reason`.
- `under_review` y `archived` quedan fuera de 14D; si se reactivan en futuro, archivar no debe borrar evidencia ni audit logs.
- El bot persiste estado conversacional con `last_step`, `last_update_id`, `telegram_user_id` y `telegram_chat_id`.
- Repetir un `telegram_update_id` ya procesado no debe duplicar solicitud, archivo, audit ni notificacion.
- Repetir el mismo documento no debe duplicar `file_assets`; el servicio deduplica por `telegram_chat_id + telegram_update_id + file_unique_id/file_id`.
