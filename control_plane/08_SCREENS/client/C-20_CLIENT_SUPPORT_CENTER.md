# C-20_CLIENT_SUPPORT_CENTER.md

## Surface

Mini App Cliente.

## Objetivo

Permitir que el cliente abra y siga tickets de soporte general o asociados a una orden propia.

## Scopes permitidos

- `client_general`
- `client_order`

## UI

- Lista de tickets propios con status, category, updated_at y ultimo resumen seguro.
- Crear ticket con:
  - scope
  - category
  - subject
  - body
  - `order_id` obligatorio cuando scope sea `client_order`
- Detalle con mensajes, eventos visibles, adjuntos propios y respuesta.
- Adjuntos permitidos: imagen/PDF segun `SUPPORT_API.md`.
- Estados: loading, empty, error, offline, forbidden, success.

## No debe mostrar

- tickets de otros usuarios
- tickets de negocio/admin
- acciones admin
- resolucion de disputa
- cambios de orden, pago, credito o anuncio
- `storage_path`, signed URLs persistidas, tokens, secretos o datos bancarios completos

## Copy obligatorio

NODO registra evidencia y estado; no recibe, retiene, transfiere ni garantiza fondos.

## Backend authority

El backend valida ownership por `requester_user_id` y por `order_id` propio. El frontend no decide permisos.
