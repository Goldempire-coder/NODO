# SECURITY_CONTRACT.md

## Principio

Escalar no puede romper seguridad.

## Auth liviana permitida

Solo para lectura no sensible de marketplace:

- `GET /api/v1/ads/search`
- opcionalmente `GET /api/v1/ads/{id}` si no revela datos privados.

Debe validar:

- firma JWT.
- expiracion JWT.
- `role` compatible.
- `status` compatible con lectura.

Debe limitar riesgo de bloqueo reciente:

- TTL maximo recomendado: 10 a 30 segundos para cache de usuario/read-session.
- Si existe invalidacion por admin, debe invalidar al suspender/bloquear usuario.
- El builder debe reportar el stale window exacto.

## Auth fuerte obligatoria

Siempre se consulta autoridad backend/DB/cache invalidable fuerte para:

- crear orden.
- reportar pago.
- revelar instrucciones.
- negocio.
- admin.
- creditos.
- soporte/chat.
- bot intake.

## Rate limits

- Marketplace read debe tener proteccion por user/IP/ruta sin llamar Redis remoto en cada request si eso degrada p95.
- Mutaciones sensibles mantienen Redis rate limit/idempotencia.

## Prohibiciones

- No exponer secretos.
- No exponer `storage_path`.
- No exponer `account_value`.
- No mover autorizacion sensible al frontend.
- No convertir frontend en fuente de permisos.
- No aceptar `surface` o query params como autoridad.

