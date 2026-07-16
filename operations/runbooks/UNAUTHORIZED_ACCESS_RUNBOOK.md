# RUNBOOK: Possible unauthorized access

Estado de validacion: NOT VALIDATED

## SINTOMA

Usuario ve datos ajenos, admin/support tiene permisos indebidos, negocio accede sin link.

## SEVERIDAD INICIAL

SEV-1.

## PRIMEROS CINCO MINUTOS

1. Preservar evidencia.
2. Bloquear sesion/usuario si hay dano activo.
3. Revisar audit logs.
4. Revisar `users.status`, `business_access_links`, `staff_profiles`, `staff_permissions`.

## MITIGACION

- Bloquear usuario o suspender access link con reason.
- Revocar staff profile si aplica.

## PROHIBICIONES

- No borrar evidencia.
- No bajar RBAC.
- No exponer datos en canal de incidente.
