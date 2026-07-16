# BAPP-20_BUSINESS_SUPPORT_CENTER.md

## Surface

Mini App Negocio.

## Objetivo

Permitir que el negocio aprobado y vinculado abra y siga tickets de soporte propios sin entrar a Admin Web.

## Scopes permitidos

- `business_general`
- `business_order`
- `business_ad`
- `business_credit`

## UI

- Lista de tickets del negocio con filtros simples por status y scope.
- Crear ticket con:
  - scope
  - category
  - subject
  - body
  - `order_id` cuando scope sea `business_order`
  - `ad_id` cuando scope sea `business_ad`
  - `credit_purchase_id` cuando scope sea `business_credit`
- Detalle con mensajes, eventos visibles, adjuntos y respuesta.
- Empty state cuando no hay tickets.
- Estados de acceso: no linked business, business suspended/blocked, forbidden.
- Estados: loading, empty, error, offline, forbidden, success.

## No debe mostrar

- tickets de otros negocios
- tickets cliente fuera de recursos propios
- panel admin
- resolucion de disputa formal
- cambios de orden, credito, anuncio, usuario o business access
- `storage_path`, signed URLs persistidas, tokens, secretos, `account_value` o datos bancarios completos

## Copy obligatorio

NODO registra evidencia y estado; no recibe, retiene, transfiere ni garantiza fondos.

## Backend authority

El backend valida `business_access_links.status = active`, negocio propio y ownership del recurso asociado.
