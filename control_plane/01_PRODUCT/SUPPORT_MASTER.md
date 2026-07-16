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

- Scope: `client_order` para cliente/remitente.
- Scope: `business_order` para negocio.
- Asociado a `orders.id`.
- Puede coexistir con chat operativo.
- No cambia estados de orden por si mismo.
- Puede escalar a disputa formal si el usuario decide y el estado lo permite.

### Soporte negocio

- Scope: `business_general`
- Asociado a `businesses.id`.
- No permite autoaprobacion ni saltar verificacion.

### Soporte por anuncio

- Scope: `business_ad`
- Asociado a `ads.id` propio del negocio.
- No cambia `ads.status`.

### Soporte por creditos

- Scope: `business_credit`
- Asociado a wallet, ledger o `credit_purchases.id` propio del negocio.
- No acredita, revierte ni ajusta creditos.

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
- En 20B escalar soporte no crea disputa nueva; solo marca el ticket como `escalated` o lo vincula a disputa existente si ya existe y el actor puede verla.
- Soporte no cambia dinero, creditos, ordenes, anuncios, roles ni access links.
- En 20C, soporte delegado usa `staff_profiles` + `staff_permissions` para limitar cola, tickets asignados, scopes, adjuntos y lecturas enmascaradas.
- `support_agent` opera tickets asignados o colas permitidas; `support_lead` puede asignar/escalar/resolver/cerrar solo con permisos activos; `operations_readonly` solo lee datos enmascarados.
- Staff delegado no resuelve disputas formales, no bloquea usuarios, no muta creditos, no aprueba negocios y no modifica `business_access_links`.

## Categorias

- `technical_issue`
- `account_access`
- `order_help`
- `payment_report_help`
- `business_access`
- `credits_help`
- `suspicious_activity`
- `other`

## Estados

Ver `support_ticket.status` en `ENUMS_AND_STATUS_MASTER.md`.
