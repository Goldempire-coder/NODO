# SUPPORT_SECURITY.md

## Objetivo

Separar soporte general, soporte por orden, chat operativo y disputa formal.

## Reglas

- Soporte general no cambia estados de orden.
- Soporte por orden no cambia estados de orden salvo escalamiento formal a disputa segun contrato.
- Chat operativo por orden no es disputa.
- Disputa formal usa `disputes` y contratos de disputa existentes.
- `support` puede responder/escalar tickets segun RBAC, pero no ejecutar acciones criticas no autorizadas.
- Admin/super_admin pueden cerrar/resolver tickets y ejecutar acciones criticas solo si el contrato del recurso lo permite.
- Adjuntos de soporte usan `file_assets.resource_type = support_ticket` o `support_message`, storage privado y nunca exponen `storage_path`.
- Audit logs de soporte no deben incluir mensajes completos sensibles, tokens, secretos, storage paths ni datos bancarios completos.

## Masking

- Listados admin muestran resumen seguro.
- Evidencia/documentos se abren con signed URL corta, permiso backend y audit cuando aplique.

