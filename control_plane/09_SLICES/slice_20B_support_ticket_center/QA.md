# QA.md

Tests obligatorios:

- remitter crea soporte general.
- remitter crea soporte por orden propia.
- remitter no crea soporte por orden ajena.
- business_owner crea soporte general de negocio propio.
- business_owner crea soporte por orden/anuncio/credito propio.
- business_owner no crea soporte por recurso ajeno.
- listar tickets propios no filtra tickets ajenos.
- admin/support listan cola con filtros y cursor pagination.
- admin/support ven detalle seguro.
- support responde ticket.
- support asigna ticket si RBAC lo permite.
- support escala ticket sin crear disputa.
- support resuelve/cierra ticket sin cambiar orden/credito/anuncio.
- support no llama resolve dispute.
- adjunto valido se guarda privado.
- MIME invalido falla.
- archivo mayor a 5 MB falla.
- response nunca expone `storage_path`.
- signed URL corta requiere reason y audit.
- audit no contiene body completo ni evidencia privada.
- rate limits aplican en create/message/upload/admin actions.
- frontend cliente/negocio/admin renderiza loading/empty/error/offline/forbidden/success.
- scan frontend/source/build sin secretos, `storage_path`, `account_value` ni claims prohibidos.
