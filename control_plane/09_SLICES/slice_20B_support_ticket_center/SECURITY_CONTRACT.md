# SECURITY_CONTRACT.md

## RBAC

- `remitter`: crea/ve/responde tickets propios.
- `business_owner`: crea/ve/responde tickets de negocio propio con access link activo.
- `support`: ve cola, responde, asigna, escala, resuelve y cierra tickets; no ejecuta acciones criticas de otros dominios.
- `admin`/`super_admin`: control total del centro de soporte.

## Prohibiciones para support

Support NO puede:
- resolver disputa formal;
- cambiar `orders.status`;
- mover creditos;
- cambiar `ads.status`;
- aprobar/rechazar pagos;
- cambiar roles;
- suspender/reactivar/bloquear usuarios;
- cambiar `business_access_links`;
- ver `storage_path`, `account_value`, tokens o secretos.

## Datos sensibles

- Bodies completos no se copian a audit metadata.
- Adjuntos se leen mediante signed URL corta solo con permiso y audit.
- Listas admin usan resumen/masking.
- Errores no revelan existencia de recursos ajenos.

## Rate limit

- Crear ticket: por actor/surface.
- Mensajes: por actor/ticket.
- Adjuntos: por actor/ticket.
- Admin assign/escalate/resolve/close: por actor.
