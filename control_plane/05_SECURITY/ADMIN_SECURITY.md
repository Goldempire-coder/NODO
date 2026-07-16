# ADMIN_SECURITY.md

Contrato de seguridad para el panel admin.

## Regla madre

El admin panel no puede depender de whitelist informal de Telegram. Debe usar sesion autenticada, rol activo, permisos por accion, audit logs y confirmaciones para acciones criticas.

## Acceso

- Solo usuarios con rol `admin` o `super_admin` activo pueden entrar.
- `support` solo puede acceder a vistas permitidas por `RBAC_PERMISSION_MATRIX.md`.
- Usuario suspendido, bloqueado o sin sesion valida no puede acceder.
- El frontend no oculta solamente; el backend debe negar la accion.

## Acciones criticas

Requieren confirmacion, nota obligatoria y audit log:

- suspender usuario
- reactivar usuario
- bloquear usuario
- aprobar negocio
- rechazar negocio
- suspender negocio
- desbloquear negocio
- vincular usuario/Telegram a negocio
- suspender/reactivar/revocar/bloquear acceso de negocio
- aprobar pago manual de creditos
- rechazar pago manual de creditos
- ajustar creditos
- resolver disputa
- cambiar riesgo de negocio
- cambiar roles admin
- asignar/escalar/resolver/cerrar tickets de soporte cuando lo requiera el contrato de soporte
- abrir signed URL de adjunto sensible de soporte

Reglas de user control:

- `suspend_user` usa `users.status = restricted`; no se crea enum `suspended` en usuarios.
- `reactivate_user` solo permite `restricted|dormant -> active` en 20A.
- `blocked -> active` queda fuera de 20A salvo contrato futuro.
- `admin` no puede mutar usuarios `admin` o `super_admin`.
- `super_admin` no puede bloquear/suspender el ultimo `super_admin active`.
- `support` es read-only.
- Excepcion 20B: `support` puede operar tickets de soporte segun RBAC (`create_support_message`, `assign_support_ticket`, `escalate_support_ticket`, `resolve_support_ticket`, `close_support_ticket`, `view_support_attachment`).
- Esa excepcion no autoriza a `support` a resolver disputas formales, cambiar ordenes, mover creditos, cambiar anuncios, roles, usuarios o `business_access_links`.
- En 20C, empleados/colaboradores usan `staff_profiles` y `staff_permissions`; `users.role` no basta para conceder permisos finos.
- Solo `super_admin` puede crear invitaciones staff, activar/suspender/revocar staff y cambiar permisos staff.
- Staff delegado puede operar soporte o lecturas enmascaradas solo dentro de permisos/scopes activos.
- Revocar/suspender staff corta sus capacidades inmediatamente sin bloquear necesariamente el usuario.
- Staff delegado nunca puede ejecutar acciones criticas de usuarios, negocios, creditos, disputas, ordenes, anuncios o access links.

Para `slice_09_admin_console`, resolver disputa esta permitido solo para
`admin` y `super_admin`; `support` conserva acceso read-only segun RBAC.

## Datos sensibles

- No mostrar datos bancarios completos por defecto.
- Revelar datos sensibles solo con permiso y audit event.
- No permitir exportaciones sensibles en MVP salvo aprobacion explicita.

## Session safety

- JWT corto.
- Refresh controlado.
- Logout/invalidation si se implementa tabla de sesiones.
- Rate limit en login/admin actions.

## Tests obligatorios

- usuario sin rol admin recibe `403`.
- `support` no puede aprobar/rechazar/ajustar.
- admin action sin reason recibe `400`.
- admin action genera audit log.
- datos sensibles aparecen enmascarados.
- exportacion sensible rechazada por defecto.
- `support` no puede suspender/reactivar/bloquear usuarios.
- no se puede bloquear el ultimo `super_admin active`.
- user status mutations requieren `Idempotency-Key`.
- soporte admin: asignar/escalar/resolver/cerrar ticket requiere RBAC, reason cuando aplique y audit.
- soporte admin: ver adjunto privado genera audit y usa signed URL corta no persistida.
- staff 20C: staff revocado/suspendido pierde acceso inmediatamente.
- staff 20C: soporte delegado no puede ejecutar acciones criticas aunque el frontend muestre un boton por error.
- staff 20C: cambios de permisos requieren reason, idempotencia y audit.

## Bloqueo

Si una accion admin mutante no tiene RBAC, reason, audit log y test, Builder debe detenerse con:

```txt
BLOCKED_BY_SECURITY_GAP
```
