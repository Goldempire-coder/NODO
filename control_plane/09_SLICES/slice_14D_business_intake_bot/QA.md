# QA.md

Pruebas requeridas para build 14D:

- webhook con secreto invalido falla.
- start crea draft.
- repetir `telegram_update_id` de start devuelve mismo resultado.
- contacto compartido valido guarda `contact_phone`.
- contacto con `contact.user_id != telegram_user_id` falla con `BOT_CONTACT_REQUIRED`.
- `business_phone` se guarda separado de `contact_phone`.
- submit sin contacto previo falla.
- submit valido deja `status = submitted`.
- submit no crea negocio activo.
- submit no crea `business_access_links`.
- submit no publica anuncios.
- upload imagen/PDF valido crea `file_assets.resource_type = business_intake`.
- upload usa `file_assets.file_type = intake_document`.
- upload no expone `storage_path`.
- upload video falla con `BOT_UPLOAD_INVALID`.
- upload mayor a 5 MB falla.
- repetir update de upload no duplica archivo ni audit.
- admin queda notificado sin datos sensibles.
- audit events creados.
- no READY_FOR_REAL_USE.
