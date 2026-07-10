# SUPPORT_MASTER.md

Contrato maestro de soporte.

## Objetivo

Separar soporte general, soporte por orden, soporte negocio, chat operativo y disputa formal.

## Tipos de soporte

### Soporte general cliente

- Scope: `client_general`
- No requiere orden.
- No cambia estados de orden.
- Puede escalar a soporte humano/admin.

### Soporte por orden

- Scope: `order_support`
- Asociado a `orders.id`.
- Puede coexistir con chat operativo.
- No cambia estados de orden por si mismo.
- Puede escalar a disputa formal si el usuario decide y el estado lo permite.

### Soporte negocio

- Scope: `business_general`
- Asociado a `businesses.id`.
- No permite autoaprobacion ni saltar verificacion.

### Chat operativo por orden

- Usa `messages` existente.
- Sirve para coordinacion entre remitente/negocio y registro de orden.
- No es disputa formal.

### Disputa formal

- Usa `disputes` existente.
- Puede afectar orden, creditos y anuncio segun contratos de disputa.
- Requiere accion explicita de apertura/escalamiento permitida.

### Admin interno

- Scope: `admin_internal`
- Para operaciones internas y seguimiento admin/support.

## Reglas

- Soporte general no cambia estados de orden.
- Soporte por orden no consume/libera creditos.
- Chat operativo no resuelve disputas.
- Support puede responder/escalar solo segun RBAC.
- Acciones criticas quedan para admin/super_admin segun contrato.
- Adjuntos usan storage privado y no exponen `storage_path`.

## Estados

Ver `support_ticket.status` en `ENUMS_AND_STATUS_MASTER.md`.
