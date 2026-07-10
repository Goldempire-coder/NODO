# DATA_CONTRACT.md

## Tablas existentes

No se requieren nuevas tablas para el MVP de slice 15.

Tablas leidas:

- `users`
- `ads`
- `businesses`
- `orders`
- `sessions`

## Indices

El builder debe verificar, no inventar:

- indices de marketplace sobre `ads.payment_method`, `ads.delivery_method`, rangos de monto, estado, tasa y fecha.
- indices de join `ads.business_id`.
- indices de `businesses.verification_status` y `risk_level` si el plan de DB lo requiere.
- indices de `users.id`, `users.status`, `users.role`.

Si el `EXPLAIN ANALYZE` muestra scan peligroso, el builder debe proponer migracion reversible con indice concreto y evidencia antes/despues.

## Cache

Cache permitida:

- L1 in-process para respuestas calientes de marketplace.
- L2 Redis para compartir cache entre workers/instancias.
- Cache de auth/usuario solo con TTL corto o invalidacion.

Cache prohibida:

- Cachear `account_value`.
- Cachear storage paths.
- Cachear documentos privados.
- Cachear permisos admin para mutaciones.
- Cachear respuestas de payment instructions.

## Invalidacion requerida

Marketplace cache debe invalidarse cuando:

- se crea anuncio.
- se actualiza anuncio.
- se pausa anuncio.
- se archiva anuncio.
- se crea orden y el anuncio sale del marketplace.
- se materializa expiracion de anuncio.
- admin suspende/bloquea negocio.
- admin cambia risk level de negocio a `restricted` o `high_risk`.

