# AW-22_STAFF_DETAIL.md

## Surface

Admin Web Desktop.

## Objetivo

Ver detalle de un perfil staff, permisos activos/revocados recientes y actividad auditada.

## Layout

- Split view desktop.
- Panel izquierdo: identidad enmascarada, rol base, staff_role, status, timestamps.
- Panel derecho: matriz de permisos, scopes, actividad y tickets asignados.
- Confirmaciones para suspender/revocar/actualizar permisos.

## Acciones

- Activar perfil staff.
- Suspender staff.
- Revocar staff.
- Actualizar permisos.
- Ver actividad limitada.

Todas las mutaciones requieren `reason`, `Idempotency-Key`, backend RBAC y audit.

## Seguridad

- Solo `super_admin` muta staff/permisos.
- No permite bloquear usuario, cambiar `users.role`, aprobar creditos, resolver disputas ni mutar ordenes/anuncios.
- Adjuntos o datos sensibles enlazados desde actividad se muestran enmascarados.

## Estados

- loading
- empty
- forbidden
- error
- success
