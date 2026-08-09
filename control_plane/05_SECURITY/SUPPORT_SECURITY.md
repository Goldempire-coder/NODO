# SUPPORT_SECURITY.md

## Objetivo

Separar soporte general, soporte por orden, chat operativo y disputa formal.

## Reglas

- Soporte general no cambia estados de orden.
- Soporte por orden no cambia estados de orden salvo escalamiento formal a disputa segun contrato.
- El reporte estructurado 42E/42F puede crear un hold operativo de publicacion
  separado. No cambia la orden, el anuncio, creditos ni capacidad financiera.
- Chat operativo por orden no es disputa.
- Soporte no se abre desde el chat operativo por orden.
- Disputa formal usa `disputes` y contratos de disputa existentes.
- `support` puede responder/escalar tickets segun RBAC, pero no ejecutar acciones criticas no autorizadas.
- Admin/super_admin pueden cerrar/resolver tickets y ejecutar acciones criticas solo si el contrato del recurso lo permite.
- Cerrar o resolver un ticket no libera un hold operativo. Admin/Super Admin, o
  Support delegado con `release_business_publication_hold`, deben usar la accion
  purpose-bound con reason, idempotencia y audit.
- Adjuntos de soporte usan `file_assets.resource_type = support_ticket` o `support_message`, storage privado y nunca exponen `storage_path`.
- Audit logs de soporte no deben incluir mensajes completos sensibles, tokens, secretos, storage paths ni datos bancarios completos.

## Masking

- Listados admin muestran resumen seguro.
- Evidencia/documentos se abren con signed URL corta, permiso backend y audit cuando aplique.
