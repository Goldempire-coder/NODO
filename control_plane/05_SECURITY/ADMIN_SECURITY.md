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

## Bloqueo

Si una accion admin mutante no tiene RBAC, reason, audit log y test, Builder debe detenerse con:

```txt
BLOCKED_BY_SECURITY_GAP
```
