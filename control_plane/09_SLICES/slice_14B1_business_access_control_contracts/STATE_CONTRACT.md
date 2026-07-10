# STATE_CONTRACT.md

## Access states

- allowed
- no_business_link
- business_not_approved
- business_suspended
- business_blocked
- user_not_active
- user_blocked
- link_suspended
- link_revoked
- link_blocked

## Link transitions

- create -> active
- active -> suspended
- suspended -> active
- active -> revoked
- suspended -> revoked
- active -> blocked
- suspended -> blocked

Reason obligatorio para suspend/revoke/block/reactivate.

## Business effects

- `business.suspended`: no publica anuncios nuevos, no toma nuevas ordenes; puede ver historial o responder casos abiertos solo con capability explicita.
- `business.blocked`: no opera, no aparece en marketplace, no confirma pagos, no marca entregas; solo estado de bloqueo/contacto soporte.
- `user.blocked`: ese usuario no usa NODO segun auth policy.
- `link.suspended/revoked/blocked`: esa persona no entra a Mini App Negocio aunque el negocio exista.
