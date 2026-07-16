# AW-21_STAFF_CENTER.md

## Surface

Admin Web Desktop.

## Objetivo

Listar y filtrar perfiles staff internos sin mezclar esta vista con Mini Apps.

## Layout

- Sidebar Admin Web.
- Top bar administrativa.
- Tabla densa con columnas: nombre, usuario, staff_role, status, permisos, ultima actividad.
- Filtros por status, staff_role y permiso.
- Busqueda por username/display name.
- Cursor pagination.
- Empty/error/forbidden/loading states.

## Acciones

- Ver detalle staff.
- Crear invitacion staff si actor es `super_admin`.
- Suspender/revocar solo desde detalle con reason.

## Seguridad

- Backend RBAC manda.
- Support/staff delegado no ve esta pantalla salvo permiso explicito de lectura administrativa.
- No exponer tokens, secretos, `storage_path`, `account_value`, datos bancarios completos ni signed URLs.

## No incluye

- Cambiar usuarios críticos directamente.
- Aprobar creditos/negocios.
- Resolver disputas.
- Exportaciones sensibles.
