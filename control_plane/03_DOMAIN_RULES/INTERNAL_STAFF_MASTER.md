# INTERNAL_STAFF_MASTER.md

Contrato maestro para delegacion interna segura en NODO.

## Objetivo

Permitir que NODO opere con empleados o colaboradores sin entregar permisos peligrosos. La delegacion interna se modela con perfiles y permisos auditables sobre usuarios existentes.

## Decision canonica

- `users.role` sigue siendo rol base y no da granularidad suficiente.
- Los roles persistentes MVP de `users.role` no cambian: `remitter`, `business_owner`, `admin`, `super_admin`, `support`.
- La granularidad interna usa:
  - `staff_profiles`
  - `staff_permissions`
  - `staff_invites`
- `staff_activity` no es tabla activa MVP; es read model sobre `audit_logs`, `support_ticket_events` y eventos `staff_*`.

## Roles internos

`staff_profiles.staff_role`:

- `support_agent`
- `support_lead`
- `operations_readonly`
- `admin`
- `super_admin`

Reglas:

- `support_agent`: opera solo tickets asignados o colas permitidas por `staff_permissions`.
- `support_lead`: puede operar cola de soporte y asignar/escalar/resolver/cerrar tickets si tiene permisos activos.
- `operations_readonly`: lectura enmascarada de usuarios, negocios, ordenes, auditoria limitada y metricas limitadas.
- `admin` y `super_admin`: reflejan operadores internos con rol base admin/super_admin; no reducen las restricciones existentes de `users.role`.
- Nadie puede suspender, revocar o bloquear el ultimo `super_admin` activo.

## Estados

`staff_profiles.status`:

- `active`
- `suspended`
- `revoked`

`staff_invites.status`:

- `pending`
- `accepted`
- `expired`
- `revoked`

`staff_permissions.status`:

- `active`
- `revoked`

## Acceso efectivo

Un staff puede entrar u operar Admin Web solo si:

- `users.status = active`.
- `staff_profiles.status = active`.
- El usuario tiene rol base compatible (`support`, `admin` o `super_admin`).
- La superficie es `admin_web`.
- El permiso requerido existe en `staff_permissions.status = active` o pertenece al rol admin/super_admin segun RBAC maestro.

La suspension/revocacion de staff no bloquea necesariamente al usuario. Bloquear o restringir al usuario sigue el contrato de usuarios/admin de 20A.

## Permisos granulares

Permisos activos:

- `view_support_queue`
- `view_assigned_support_tickets`
- `reply_support_ticket`
- `assign_support_ticket`
- `escalate_support_ticket`
- `resolve_support_ticket`
- `close_support_ticket`
- `view_support_attachment`
- `view_users_masked`
- `view_businesses_masked`
- `view_orders_masked`
- `view_audit_limited`
- `view_metrics_limited`

Scopes permitidos:

- `assigned_only`
- `queue_scope`
- `category_scope`
- `global_readonly`

Reglas:

- Los datos se muestran enmascarados por defecto.
- Adjuntos privados requieren `view_support_attachment`, reason no vacio y audit.
- `support_agent` no obtiene acceso global por defecto.
- `support_lead` puede asignar/escalar/resolver/cerrar tickets solo si el permiso esta activo.
- `operations_readonly` no muta tickets ni recursos de dominio.

## Permisos prohibidos para staff delegado

Staff delegado no puede:

- `block_user`
- `suspend_user`
- `change_user_role`
- `mutate_business_access_links`
- `approve_business`
- `reject_business`
- `approve_credit_payment`
- `reject_credit_payment`
- `manual_credit_adjustment`
- `resolve_dispute`
- `mutate_orders`
- `mutate_ads`
- `mutate_credits`

Estas acciones siguen reservadas a `admin`/`super_admin` segun contratos existentes y nunca se habilitan por permiso staff.

## Invitacion y activacion

- Solo `super_admin` crea invitaciones staff.
- La invitacion vincula un usuario existente por `target_user_id`, `target_telegram_id` o `target_username`.
- No se envian secretos al frontend.
- Si existe token/codigo de invitacion, se guarda solo como hash y no se vuelve a mostrar despues de crearse.
- La invitacion expira en `expires_at`.
- Activar staff requiere usuario existente, `users.status = active`, rol base compatible y reason.
- Revocar staff no borra usuario, tickets, audit ni mensajes.

## Relacion con soporte

- Soporte 20B sigue separado de chat operativo y disputa formal.
- Staff puede operar tickets solo dentro de permisos y scopes.
- Resolver/cerrar un ticket no resuelve disputa formal.
- Escalar soporte no cambia `orders.status`, creditos, anuncios, usuarios ni `business_access_links`.

## Auditoria

Eventos canonicos:

- `staff_invite_created`
- `staff_invite_expired`
- `staff_activated`
- `staff_suspended`
- `staff_revoked`
- `staff_permissions_updated`
- `staff_activity_viewed`
- `staff_ticket_assigned`
- `staff_access_denied`

Audit metadata no debe contener tokens, storage paths, signed URLs, datos bancarios completos, cuerpos completos de mensajes ni adjuntos privados.

## Fuera de scope

- SSO corporativo.
- Roles por departamento complejos.
- Exportaciones sensibles.
- Macros/IA para soporte.
- Permitir staff externo en Mini Apps.
- Delegar aprobaciones de creditos, negocios, disputas o mutaciones de usuarios.
