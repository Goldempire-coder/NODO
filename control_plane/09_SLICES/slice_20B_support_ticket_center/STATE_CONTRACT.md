# STATE_CONTRACT.md

## support_ticket.status

Estados canonicos 20B:
- `open`
- `waiting_support`
- `waiting_user`
- `escalated`
- `resolved`
- `closed`

No se usan en 20B:
- estado separado de espera por negocio; se usa `waiting_user`.
- estado separado de ticket vinculado a disputa; el vinculo a disputa existente es metadata/evento, no status.

## Transiciones permitidas

- `open -> waiting_support`
- `waiting_support -> waiting_user`
- `waiting_user -> waiting_support`
- `waiting_support -> escalated`
- `escalated -> waiting_support`
- `waiting_support -> resolved`
- `escalated -> resolved`
- `resolved -> closed`

## Transiciones prohibidas

- Cualquier transicion desde `closed`.
- `closed -> open`.
- `resolved -> waiting_support` salvo contrato futuro de reopen.
- Soporte no cambia `orders.status`.
- Soporte no crea ni resuelve disputa formal en 20B.
- Soporte no mueve creditos, no cambia `ads.status` y no modifica access links.

## Escalamiento

En 20B, escalar significa marcar ticket `escalated` y crear evento.

Permitido:
- vincular metadata a una disputa existente si ya existe y el actor puede verla.

Prohibido:
- crear disputa nueva desde soporte;
- llamar `POST /api/v1/orders/{id}/disputes`;
- llamar `POST /api/v1/admin/disputes/{id}/resolve`;
- cambiar orden/credito/anuncio.
