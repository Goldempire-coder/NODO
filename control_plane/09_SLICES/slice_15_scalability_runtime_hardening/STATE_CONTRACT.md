# STATE_CONTRACT.md

## Estados de producto

No se agregan estados de dominio.

No se cambian:

- `ad.status`
- `order.status`
- `business.verification_status`
- `business.risk_level`
- `user.status`
- `business_access_links.status`

## Estados runtime permitidos

El builder puede usar estados internos de capacidad:

- `healthy`
- `degraded`
- `db_pool_saturated`
- `cache_unavailable`
- `rate_limited`

Estos estados no son enums de dominio persistente salvo contrato futuro.

