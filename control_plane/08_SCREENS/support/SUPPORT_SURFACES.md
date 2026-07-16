# SUPPORT_SURFACES.md

## Superficies de soporte

- Cliente: soporte general `client_general` y soporte por orden `client_order`.
- Negocio: soporte general `business_general`, soporte por orden `business_order`, soporte por anuncio `business_ad` y soporte por creditos `business_credit`.
- Admin/support: cola de tickets, detalle, respuesta, asignacion, escalamiento, resolucion, cierre, eventos y adjuntos.

## Pantallas canonicas 20B

- `client/C-20_CLIENT_SUPPORT_CENTER.md`
- `business_app/BAPP-20_BUSINESS_SUPPORT_CENTER.md`
- `admin_web/AW-20_SUPPORT_TICKET_CENTER.md`

## Diferencias obligatorias

- Chat operativo por orden: comunicacion entre partes sobre una orden.
- Soporte ticket: solicitud de ayuda con NODO; no cambia estados de orden.
- Disputa formal: flujo gobernado que puede afectar orden/creditos/anuncio segun contratos de disputa.
- Escalar soporte en 20B no crea disputa formal; solo cambia `support_tickets.status = escalated` o vincula una disputa existente como contexto autorizado.

## Adjuntos

- Adjuntos de soporte usan `file_assets`.
- `resource_type = support_ticket|support_message`.
- `file_type = support_attachment`.
- MIME permitido: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`.
- Tamano maximo: 5 MB.
- Nunca exponer `storage_path`.
- Admin/support obtienen signed URL corta solo con RBAC y audit `support_attachment_viewed`.

## Copy obligatorio

NODO registra evidencia y estado; no recibe, retiene, transfiere ni garantiza fondos.
