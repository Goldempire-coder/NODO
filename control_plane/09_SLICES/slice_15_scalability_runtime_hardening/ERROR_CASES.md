# ERROR_CASES.md

## Errores existentes

- `UNAUTHENTICATED`
- `FORBIDDEN`
- `RATE_LIMITED`
- `VALIDATION_ERROR`
- `INTERNAL_ERROR`
- `DATABASE_UNAVAILABLE`
- `REDIS_UNAVAILABLE`

## Errores runtime permitidos si se agregan

- `RUNTIME_CAPACITY_EXCEEDED`
- `CACHE_UNAVAILABLE`
- `DB_POOL_SATURATED`

## UX

Para marketplace, errores temporales deben mostrarse como:

```txt
Estamos ajustando la conexion. Intenta de nuevo en unos segundos.
```

No mostrar stack traces ni nombres internos de base de datos.

