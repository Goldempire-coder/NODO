# STATE_CONTRACT.md

## staff_profiles.status

- `active`
- `suspended`
- `revoked`

Transiciones:

- invite/activation -> `active`
- `active -> suspended`
- `suspended -> active`
- `active -> revoked`
- `suspended -> revoked`

## staff_invites.status

- `pending`
- `accepted`
- `expired`
- `revoked`

Transiciones:

- `pending -> accepted`
- `pending -> expired`
- `pending -> revoked`

## staff_permissions.status

- `active`
- `revoked`

Transiciones:

- grant -> `active`
- `active -> revoked`

Revocar permiso debe bloquear capacidad inmediatamente.
